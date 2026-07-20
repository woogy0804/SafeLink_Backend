"""Optional fault-tolerant Redis JSON cache for shared feature metadata."""

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

import redis


REDIS_URL_ENVIRONMENT = "SAFELINK_REDIS_URL"
REDIS_SOCKET_TIMEOUT_SECONDS = 0.2


@dataclass(frozen=True)
class RedisCacheValue:
    payload: dict[str, Any]
    ttl_seconds: int


class RedisJsonCache:
    def __init__(self, client, *, namespace: str) -> None:
        self._client = client
        self._namespace = namespace.strip(":")

    @classmethod
    def from_environment(cls, *, namespace: str) -> Optional["RedisJsonCache"]:
        redis_url = os.getenv(REDIS_URL_ENVIRONMENT)
        if not redis_url:
            return None
        try:
            client = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
                socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
                retry_on_timeout=False,
            )
        except (redis.RedisError, TypeError, ValueError):
            return None
        return cls(client, namespace=namespace)

    def _key(self, key: str) -> str:
        return f"{self._namespace}:{key}"

    def get(self, key: str) -> Optional[RedisCacheValue]:
        namespaced_key = self._key(key)
        try:
            with self._client.pipeline(transaction=False) as pipeline:
                pipeline.get(namespaced_key)
                pipeline.ttl(namespaced_key)
                raw_payload, ttl_seconds = pipeline.execute()
            if raw_payload is None or int(ttl_seconds) <= 0:
                return None
            payload = json.loads(raw_payload)
            if not isinstance(payload, dict):
                return None
            return RedisCacheValue(
                payload=payload,
                ttl_seconds=int(ttl_seconds),
            )
        except (redis.RedisError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def set(self, key: str, payload: dict[str, Any], *, ttl_seconds: int) -> bool:
        if ttl_seconds <= 0:
            return False
        try:
            return bool(
                self._client.set(
                    self._key(key),
                    json.dumps(payload, ensure_ascii=True, separators=(",", ":")),
                    ex=ttl_seconds,
                )
            )
        except (redis.RedisError, TypeError, ValueError):
            return False
