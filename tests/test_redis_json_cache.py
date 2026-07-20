import json
import os
import unittest
from unittest.mock import patch

import redis

from features.redis_json_cache import RedisJsonCache


class FakePipeline:
    def __init__(self, result):
        self.result = result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def get(self, key):
        return self

    def ttl(self, key):
        return self

    def execute(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeRedisClient:
    def __init__(self, pipeline_result=None, set_result=True):
        self.pipeline_result = pipeline_result
        self.set_result = set_result
        self.set_calls = []

    def pipeline(self, transaction=False):
        return FakePipeline(self.pipeline_result)

    def set(self, key, value, ex):
        self.set_calls.append((key, value, ex))
        if isinstance(self.set_result, Exception):
            raise self.set_result
        return self.set_result


class TestRedisJsonCache(unittest.TestCase):
    def test_is_disabled_when_environment_url_is_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(
                RedisJsonCache.from_environment(namespace="test")
            )

    def test_invalid_environment_url_disables_shared_cache(self):
        with patch.dict(
            os.environ,
            {"SAFELINK_REDIS_URL": "not-a-redis-url"},
        ):
            self.assertIsNone(
                RedisJsonCache.from_environment(namespace="test")
            )

    def test_reads_payload_and_remaining_ttl(self):
        client = FakeRedisClient(
            pipeline_result=[json.dumps({"value": 1}), 120]
        )
        cache = RedisJsonCache(client, namespace="test")

        result = cache.get("example")

        self.assertEqual(result.payload, {"value": 1})
        self.assertEqual(result.ttl_seconds, 120)

    def test_writes_namespaced_json_with_expiration(self):
        client = FakeRedisClient()
        cache = RedisJsonCache(client, namespace="test")

        self.assertTrue(cache.set("example", {"value": 1}, ttl_seconds=60))

        key, raw_payload, ttl = client.set_calls[0]
        self.assertEqual(key, "test:example")
        self.assertEqual(json.loads(raw_payload), {"value": 1})
        self.assertEqual(ttl, 60)

    def test_redis_failure_falls_back_to_cache_miss(self):
        client = FakeRedisClient(
            pipeline_result=redis.RedisError("unavailable"),
            set_result=redis.RedisError("unavailable"),
        )
        cache = RedisJsonCache(client, namespace="test")

        self.assertIsNone(cache.get("example"))
        self.assertFalse(cache.set("example", {"value": 1}, ttl_seconds=60))


if __name__ == "__main__":
    unittest.main()
