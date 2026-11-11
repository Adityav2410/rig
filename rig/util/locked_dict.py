import threading
from collections.abc import Callable, Hashable


class LockedDict[K: Hashable, V]:
    """A dict that several threads can share.

    Single reads and writes on a plain dict are already atomic in CPython. What this adds is
    `get_or_create`: look up a key and, if it's missing, build and store its value as one step.
    Without the lock, two threads that miss at the same moment could each store a different
    value, and the two would no longer share one. The factory runs only on a miss.
    """

    def __init__(self) -> None:
        self._data: dict[K, V] = {}
        self._lock = threading.Lock()

    def get_or_create(self, key: K, factory: Callable[[], V]) -> V:
        with self._lock:
            if key not in self._data:
                self._data[key] = factory()
            return self._data[key]

    def __setitem__(self, key: K, value: V) -> None:
        with self._lock:
            self._data[key] = value

    def pop(self, key: K) -> V | None:
        """Remove and return the value for `key`, or None if it isn't there."""
        with self._lock:
            return self._data.pop(key, None)
