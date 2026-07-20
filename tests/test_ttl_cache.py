import unittest

from features.ttl_cache import TtlCache


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TestTtlCache(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.cache = TtlCache(
            max_entries=2,
            default_ttl_seconds=10,
            clock=self.clock,
        )

    def test_returns_value_before_expiration(self):
        self.cache.set("example.com", "value")
        self.clock.advance(9)

        self.assertEqual(self.cache.get("example.com"), "value")

    def test_removes_value_at_expiration(self):
        self.cache.set("example.com", "value")
        self.clock.advance(10)

        self.assertIsNone(self.cache.get("example.com"))
        self.assertEqual(len(self.cache), 0)

    def test_custom_ttl_overrides_default(self):
        self.cache.set("example.com", "value", ttl_seconds=2)
        self.clock.advance(2)

        self.assertIsNone(self.cache.get("example.com"))

    def test_evicts_least_recently_used_entry(self):
        self.cache.set("first", 1)
        self.cache.set("second", 2)
        self.assertEqual(self.cache.get("first"), 1)

        self.cache.set("third", 3)

        self.assertEqual(self.cache.get("first"), 1)
        self.assertIsNone(self.cache.get("second"))
        self.assertEqual(self.cache.get("third"), 3)

    def test_clear_removes_all_entries(self):
        self.cache.set("first", 1)
        self.cache.set("second", 2)

        self.cache.clear()

        self.assertEqual(len(self.cache), 0)

    def test_rejects_invalid_configuration_and_ttl(self):
        with self.assertRaises(ValueError):
            TtlCache(max_entries=0, default_ttl_seconds=10)
        with self.assertRaises(ValueError):
            TtlCache(max_entries=1, default_ttl_seconds=0)
        with self.assertRaises(ValueError):
            self.cache.set("key", "value", ttl_seconds=0)


if __name__ == "__main__":
    unittest.main()
