"""도메인 등록정보 Feature가 공유하는 RDAP 조회 컨텍스트."""

import json
import os
from functools import lru_cache
from hashlib import sha256
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote, urljoin

import requests

from features.domain_utils import get_registered_domain_from_url
from features.safe_http import (
    CONNECT_TIMEOUT,
    MAX_REDIRECTS,
    READ_TIMEOUT,
    REDIRECT_STATUS_CODES,
    REQUEST_HEADERS,
    RedirectLimitError,
    SafeHttpError,
    _close_response,
    _read_limited_text,
    _response_headers,
    validate_public_destination,
)
from features.redis_json_cache import RedisJsonCache
from features.ttl_cache import TtlCache


DEFAULT_RDAP_BASE_URL = "https://rdap.org"
RDAP_CONTENT_TYPES = {"application/rdap+json", "application/json"}
RDAP_HEADERS = {
    **REQUEST_HEADERS,
    "Accept": "application/rdap+json, application/json",
}
RDAP_CACHE_TTL_SECONDS = 24 * 60 * 60
RDAP_FAILURE_CACHE_TTL_SECONDS = 5 * 60
RDAP_CACHE_MAX_ENTRIES = 2048


@dataclass(frozen=True)
class DomainAnalysisContext:
    registered_domain: Optional[str]
    creation_date: Optional[datetime]
    expiration_date: Optional[datetime]
    lookup_failed: bool


_DOMAIN_CONTEXT_CACHE: TtlCache[tuple[str, str], DomainAnalysisContext] = TtlCache(
    max_entries=RDAP_CACHE_MAX_ENTRIES,
    default_ttl_seconds=RDAP_CACHE_TTL_SECONDS,
)


def _failed_context(registered_domain: Optional[str]) -> DomainAnalysisContext:
    return DomainAnalysisContext(
        registered_domain=registered_domain,
        creation_date=None,
        expiration_date=None,
        lookup_failed=True,
    )


def clear_domain_context_cache() -> None:
    """Clear the process-local RDAP cache (primarily useful for tests)."""

    _DOMAIN_CONTEXT_CACHE.clear()
    _shared_domain_cache.cache_clear()


@lru_cache(maxsize=1)
def _shared_domain_cache() -> Optional[RedisJsonCache]:
    return RedisJsonCache.from_environment(namespace="safelink:rdap:v1")


def _shared_cache_key(cache_key: tuple[str, str]) -> str:
    base_url, registered_domain = cache_key
    base_url_hash = sha256(base_url.encode("utf-8")).hexdigest()[:16]
    return f"{base_url_hash}:{registered_domain}"


def _serialize_domain_context(context: DomainAnalysisContext) -> dict:
    return {
        "registered_domain": context.registered_domain,
        "creation_date": (
            context.creation_date.isoformat() if context.creation_date else None
        ),
        "expiration_date": (
            context.expiration_date.isoformat() if context.expiration_date else None
        ),
        "lookup_failed": context.lookup_failed,
    }


def _deserialize_domain_context(
    payload: dict,
    *,
    expected_domain: str,
) -> Optional[DomainAnalysisContext]:
    if payload.get("registered_domain") != expected_domain:
        return None
    lookup_failed = payload.get("lookup_failed")
    if not isinstance(lookup_failed, bool):
        return None

    creation_date = _parse_rdap_datetime(payload.get("creation_date"))
    expiration_date = _parse_rdap_datetime(payload.get("expiration_date"))
    if payload.get("creation_date") is not None and creation_date is None:
        return None
    if payload.get("expiration_date") is not None and expiration_date is None:
        return None
    return DomainAnalysisContext(
        registered_domain=expected_domain,
        creation_date=creation_date,
        expiration_date=expiration_date,
        lookup_failed=lookup_failed,
    )


def _get_shared_context(
    cache_key: tuple[str, str],
) -> Optional[DomainAnalysisContext]:
    shared_cache = _shared_domain_cache()
    if shared_cache is None:
        return None
    cached_value = shared_cache.get(_shared_cache_key(cache_key))
    if cached_value is None:
        return None
    context = _deserialize_domain_context(
        cached_value.payload,
        expected_domain=cache_key[1],
    )
    if context is None:
        return None
    maximum_ttl = (
        RDAP_FAILURE_CACHE_TTL_SECONDS
        if context.lookup_failed
        else RDAP_CACHE_TTL_SECONDS
    )
    _DOMAIN_CONTEXT_CACHE.set(
        cache_key,
        context,
        ttl_seconds=min(maximum_ttl, max(1, cached_value.ttl_seconds)),
    )
    return context


def _set_cached_context(
    cache_key: tuple[str, str],
    context: DomainAnalysisContext,
    *,
    ttl_seconds: int,
) -> None:
    _DOMAIN_CONTEXT_CACHE.set(cache_key, context, ttl_seconds=ttl_seconds)
    shared_cache = _shared_domain_cache()
    if shared_cache is not None:
        shared_cache.set(
            _shared_cache_key(cache_key),
            _serialize_domain_context(context),
            ttl_seconds=ttl_seconds,
        )


def _rdap_base_url() -> str:
    return os.getenv("SAFELINK_RDAP_BASE_URL", DEFAULT_RDAP_BASE_URL).rstrip("/")


def _domain_cache_key(registered_domain: str) -> tuple[str, str]:
    return _rdap_base_url(), registered_domain.lower()


def _parse_rdap_datetime(value) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None

    normalized_value = value.strip()
    if normalized_value.endswith(("Z", "z")):
        normalized_value = f"{normalized_value[:-1]}+00:00"

    try:
        parsed_date = datetime.fromisoformat(normalized_value)
    except ValueError:
        return None

    if parsed_date.tzinfo is None:
        parsed_date = parsed_date.replace(tzinfo=timezone.utc)
    return parsed_date.astimezone(timezone.utc)


def _parse_domain_events(payload: dict) -> tuple[Optional[datetime], Optional[datetime]]:
    creation_dates = []
    expiration_dates = []

    events = payload.get("events", [])
    if not isinstance(events, list):
        return None, None

    for event in events:
        if not isinstance(event, dict):
            continue

        action = str(event.get("eventAction", "")).strip().lower()
        event_date = _parse_rdap_datetime(event.get("eventDate"))
        if event_date is None:
            continue

        if action == "registration":
            creation_dates.append(event_date)
        elif action == "expiration":
            expiration_dates.append(event_date)

    creation_date = min(creation_dates) if creation_dates else None
    expiration_date = max(expiration_dates) if expiration_dates else None
    return creation_date, expiration_date


def _validate_rdap_content_type(response) -> None:
    content_type = _response_headers(response).get("Content-Type", "")
    if not content_type:
        return

    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type not in RDAP_CONTENT_TYPES and not media_type.endswith("+json"):
        raise SafeHttpError("RDAP JSON 응답이 아닙니다.")


def _fetch_rdap_payload(registered_domain: str) -> dict:
    current_url = f"{_rdap_base_url()}/domain/{quote(registered_domain, safe='.-')}"

    for redirect_count in range(MAX_REDIRECTS + 1):
        validate_public_destination(current_url)
        response = requests.get(
            current_url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            allow_redirects=False,
            stream=True,
            headers=RDAP_HEADERS,
        )

        try:
            status_code = int(getattr(response, "status_code", 200))
            if status_code in REDIRECT_STATUS_CODES:
                location = _response_headers(response).get("Location")
                if not location:
                    raise SafeHttpError("RDAP redirect 응답에 Location이 없습니다.")
                if redirect_count >= MAX_REDIRECTS:
                    raise RedirectLimitError("RDAP redirect 횟수를 초과했습니다.")
                current_url = urljoin(current_url, location)
                continue

            response.raise_for_status()
            _validate_rdap_content_type(response)
            payload = json.loads(_read_limited_text(response))
            if not isinstance(payload, dict):
                raise SafeHttpError("RDAP 응답 형식이 올바르지 않습니다.")
            return payload
        finally:
            _close_response(response)

    raise RedirectLimitError("RDAP redirect 횟수를 초과했습니다.")


def fetch_domain_context(url: str) -> DomainAnalysisContext:
    """URL 등록 도메인의 생성일과 만료일을 RDAP 조회 한 번으로 반환한다."""

    registered_domain = get_registered_domain_from_url(url)
    if registered_domain is None:
        return _failed_context(None)

    try:
        cache_key = _domain_cache_key(registered_domain)
    except UnicodeError:
        return _failed_context(registered_domain)

    cached_context = _DOMAIN_CONTEXT_CACHE.get(cache_key)
    if cached_context is not None:
        return cached_context
    shared_context = _get_shared_context(cache_key)
    if shared_context is not None:
        return shared_context

    try:
        payload = _fetch_rdap_payload(registered_domain)
        creation_date, expiration_date = _parse_domain_events(payload)
        context = DomainAnalysisContext(
            registered_domain=registered_domain,
            creation_date=creation_date,
            expiration_date=expiration_date,
            lookup_failed=False,
        )
        _set_cached_context(
            cache_key,
            context,
            ttl_seconds=RDAP_CACHE_TTL_SECONDS,
        )
        return context
    except Exception:
        context = _failed_context(registered_domain)
        _set_cached_context(
            cache_key,
            context,
            ttl_seconds=RDAP_FAILURE_CACHE_TTL_SECONDS,
        )
        return context
