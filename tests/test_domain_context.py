import json
import os
import unittest
from unittest.mock import patch

from features.domain_context import (
    RDAP_CACHE_MAX_ENTRIES,
    RDAP_CACHE_TTL_SECONDS,
    RDAP_FAILURE_CACHE_TTL_SECONDS,
    _parse_domain_events,
    clear_domain_context_cache,
    fetch_domain_context,
)
from features.redis_json_cache import RedisCacheValue
from features.ttl_cache import TtlCache


class FakeResponse:
    def __init__(self, payload=None, *, status_code=200, headers=None, text=None):
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "application/rdap+json"}
        self.encoding = "utf-8"
        if text is not None:
            self._body = text.encode("utf-8")
        else:
            self._body = json.dumps(payload or {}).encode("utf-8")
        self.closed = False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield self._body

    def close(self):
        self.closed = True


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FakeSharedCache:
    def __init__(self, cached_value=None):
        self.cached_value = cached_value
        self.get_calls = []
        self.set_calls = []

    def get(self, key):
        self.get_calls.append(key)
        return self.cached_value

    def set(self, key, payload, ttl_seconds):
        self.set_calls.append((key, payload, ttl_seconds))
        return True


class TestDomainContext(unittest.TestCase):
    def setUp(self):
        clear_domain_context_cache()
        self.addCleanup(clear_domain_context_cache)

        destination_patcher = patch(
            "features.domain_context.validate_public_destination",
            side_effect=lambda url: url,
        )
        destination_patcher.start()
        self.addCleanup(destination_patcher.stop)

        environment_patcher = patch.dict(
            os.environ,
            {"SAFELINK_RDAP_BASE_URL": "https://rdap.test"},
        )
        environment_patcher.start()
        self.addCleanup(environment_patcher.stop)

    def test_parses_registration_and_expiration_events(self):
        payload = {
            "events": [
                {"eventAction": "registration", "eventDate": "2021-01-01T00:00:00Z"},
                {"eventAction": "registration", "eventDate": "2020-01-01T00:00:00Z"},
                {"eventAction": "expiration", "eventDate": "2029-01-01T00:00:00Z"},
                {"eventAction": "expiration", "eventDate": "2030-01-01T00:00:00Z"},
            ]
        }

        creation_date, expiration_date = _parse_domain_events(payload)

        self.assertEqual(creation_date.isoformat(), "2020-01-01T00:00:00+00:00")
        self.assertEqual(expiration_date.isoformat(), "2030-01-01T00:00:00+00:00")

    def test_fetches_one_rdap_response_for_both_dates(self):
        payload = {
            "objectClassName": "domain",
            "events": [
                {"eventAction": "registration", "eventDate": "2020-01-01T00:00:00Z"},
                {"eventAction": "expiration", "eventDate": "2030-01-01T00:00:00Z"},
            ],
        }
        response = FakeResponse(payload)
        with patch(
            "features.domain_context.requests.get",
            return_value=response,
        ) as mock_get:
            context = fetch_domain_context("https://www.example.com/path")

        self.assertFalse(context.lookup_failed)
        self.assertEqual(context.registered_domain, "example.com")
        self.assertEqual(context.creation_date.year, 2020)
        self.assertEqual(context.expiration_date.year, 2030)
        self.assertEqual(mock_get.call_count, 1)
        self.assertTrue(response.closed)

    def test_reuses_cached_response_for_same_registered_domain(self):
        response = FakeResponse(
            {
                "events": [
                    {
                        "eventAction": "registration",
                        "eventDate": "2020-01-01T00:00:00Z",
                    }
                ]
            }
        )
        with patch(
            "features.domain_context.requests.get",
            return_value=response,
        ) as mock_get:
            first_context = fetch_domain_context("https://www.example.com/path")
            second_context = fetch_domain_context("https://login.example.com")

        self.assertIs(first_context, second_context)
        self.assertEqual(mock_get.call_count, 1)

    def test_success_cache_expires_after_24_hours(self):
        clock = FakeClock()
        cache = TtlCache(
            max_entries=RDAP_CACHE_MAX_ENTRIES,
            default_ttl_seconds=RDAP_CACHE_TTL_SECONDS,
            clock=clock,
        )
        responses = [
            FakeResponse({"events": []}),
            FakeResponse({"events": []}),
        ]

        with patch("features.domain_context._DOMAIN_CONTEXT_CACHE", cache):
            with patch(
                "features.domain_context.requests.get",
                side_effect=responses,
            ) as mock_get:
                fetch_domain_context("https://example.com")
                clock.advance(RDAP_CACHE_TTL_SECONDS - 1)
                fetch_domain_context("https://example.com")
                self.assertEqual(mock_get.call_count, 1)

                clock.advance(1)
                fetch_domain_context("https://example.com")

        self.assertEqual(mock_get.call_count, 2)

    def test_failed_lookup_is_retried_after_short_ttl(self):
        clock = FakeClock()
        cache = TtlCache(
            max_entries=RDAP_CACHE_MAX_ENTRIES,
            default_ttl_seconds=RDAP_CACHE_TTL_SECONDS,
            clock=clock,
        )
        responses = [
            FakeResponse(text="not-json"),
            FakeResponse({"events": []}),
        ]

        with patch("features.domain_context._DOMAIN_CONTEXT_CACHE", cache):
            with patch(
                "features.domain_context.requests.get",
                side_effect=responses,
            ) as mock_get:
                first_context = fetch_domain_context("https://example.com")
                second_context = fetch_domain_context("https://example.com")
                self.assertTrue(first_context.lookup_failed)
                self.assertIs(first_context, second_context)
                self.assertEqual(mock_get.call_count, 1)

                clock.advance(RDAP_FAILURE_CACHE_TTL_SECONDS)
                retried_context = fetch_domain_context("https://example.com")

        self.assertFalse(retried_context.lookup_failed)
        self.assertEqual(mock_get.call_count, 2)

    def test_cache_is_separated_by_rdap_base_url(self):
        responses = [
            FakeResponse({"events": []}),
            FakeResponse({"events": []}),
        ]
        with patch(
            "features.domain_context.requests.get",
            side_effect=responses,
        ) as mock_get:
            fetch_domain_context("https://example.com")
            os.environ["SAFELINK_RDAP_BASE_URL"] = "https://other-rdap.test"
            fetch_domain_context("https://example.com")

        self.assertEqual(mock_get.call_count, 2)

    def test_reads_context_from_shared_redis_cache(self):
        shared_cache = FakeSharedCache(
            RedisCacheValue(
                payload={
                    "registered_domain": "example.com",
                    "creation_date": "2020-01-01T00:00:00+00:00",
                    "expiration_date": "2030-01-01T00:00:00+00:00",
                    "lookup_failed": False,
                },
                ttl_seconds=120,
            )
        )
        with patch(
            "features.domain_context._shared_domain_cache",
            return_value=shared_cache,
        ):
            with patch("features.domain_context.requests.get") as mock_get:
                context = fetch_domain_context("https://example.com")

        self.assertFalse(context.lookup_failed)
        self.assertEqual(context.creation_date.year, 2020)
        self.assertEqual(context.expiration_date.year, 2030)
        self.assertEqual(len(shared_cache.get_calls), 1)
        mock_get.assert_not_called()

    def test_writes_successful_context_to_shared_redis_cache(self):
        shared_cache = FakeSharedCache()
        response = FakeResponse({"events": []})
        with patch(
            "features.domain_context._shared_domain_cache",
            return_value=shared_cache,
        ):
            with patch(
                "features.domain_context.requests.get",
                return_value=response,
            ):
                context = fetch_domain_context("https://example.com")

        self.assertFalse(context.lookup_failed)
        self.assertEqual(len(shared_cache.set_calls), 1)
        _, payload, ttl_seconds = shared_cache.set_calls[0]
        self.assertEqual(payload["registered_domain"], "example.com")
        self.assertEqual(ttl_seconds, RDAP_CACHE_TTL_SECONDS)

    def test_follows_rdap_redirect_and_validates_each_destination(self):
        redirect_response = FakeResponse(
            status_code=302,
            headers={"Location": "https://registry.test/domain/example.com"},
        )
        final_response = FakeResponse(
            {"events": []},
            headers={"Content-Type": "application/json"},
        )
        with patch(
            "features.domain_context.requests.get",
            side_effect=[redirect_response, final_response],
        ):
            with patch(
                "features.domain_context.validate_public_destination",
                side_effect=lambda url: url,
            ) as mock_validate:
                context = fetch_domain_context("https://example.com")

        self.assertFalse(context.lookup_failed)
        self.assertEqual(mock_validate.call_count, 2)

    def test_returns_failed_context_for_invalid_json(self):
        response = FakeResponse(text="not-json")
        with patch("features.domain_context.requests.get", return_value=response):
            context = fetch_domain_context("https://example.com")

        self.assertTrue(context.lookup_failed)
        self.assertIsNone(context.creation_date)
        self.assertIsNone(context.expiration_date)

    def test_missing_events_are_unknown_not_lookup_failure(self):
        response = FakeResponse({"objectClassName": "domain"})
        with patch("features.domain_context.requests.get", return_value=response):
            context = fetch_domain_context("https://example.com")

        self.assertFalse(context.lookup_failed)
        self.assertIsNone(context.creation_date)
        self.assertIsNone(context.expiration_date)


if __name__ == "__main__":
    unittest.main()
