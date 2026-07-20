"""Small thread-safe TTL cache used by network-backed feature lookups."""

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Callable, Generic, Optional, TypeVar


K = TypeVar("K")
V = TypeVar("V")


@dataclass(frozen=True)
class _CacheEntry(Generic[V]):
    value: V
    expires_at: float


class TtlCache(Generic[K, V]):
    """A bounded in-process TTL cache with least-recently-used eviction."""

    def __init__(
        self,
        *,
        max_entries: int,
        default_ttl_seconds: float,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        if default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds must be greater than 0")

        self._max_entries = max_entries
        self._default_ttl_seconds = default_ttl_seconds
        self._clock = clock
        self._entries: OrderedDict[K, _CacheEntry[V]] = OrderedDict()
        self._lock = RLock()

    def get(self, key: K) -> Optional[V]:
        """Return a live value and refresh its LRU position, or ``None``."""

        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None

            if entry.expires_at <= self._clock():
                del self._entries[key]
                return None

            self._entries.move_to_end(key)
            return entry.value

    def set(
        self,
        key: K,
        value: V,
        *,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        """Store a value until its TTL expires."""

        ttl = self._default_ttl_seconds if ttl_seconds is None else ttl_seconds
        if ttl <= 0:
            raise ValueError("ttl_seconds must be greater than 0")

        with self._lock:
            now = self._clock()
            self._remove_expired(now)
            self._entries[key] = _CacheEntry(value=value, expires_at=now + ttl)
            self._entries.move_to_end(key)

            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        """Remove all cached values."""

        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            self._remove_expired(self._clock())
            return len(self._entries)

    def _remove_expired(self, now: float) -> None:
        expired_keys = [
            key
            for key, entry in self._entries.items()
            if entry.expires_at <= now
        ]
        for key in expired_keys:
            del self._entries[key]
