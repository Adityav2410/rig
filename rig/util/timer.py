import time
from typing import Self


class Timer:
    def __init__(self) -> None:
        self._start_s: float | None = None
        self._end_s: float | None = None

    def start(self) -> None:
        self._start_s = time.monotonic()

    def reset(self) -> None:
        self._start_s = None
        self._end_s = None

    def restart(self) -> None:
        self.reset()
        self.start()

    def stop(self) -> None:
        self._end_s = time.monotonic()

    def __enter__(self) -> Self:
        self._start_s = time.monotonic()
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self._end_s = time.monotonic()

    def elapsed_s(self) -> float:
        if self._start_s is None:
            raise ValueError("Timer has not been started.")
        return (
            self._end_s - self._start_s
            if self._end_s is not None
            else time.monotonic() - self._start_s
        )

    def elapsed_ms(self) -> int:
        return int(self.elapsed_s() * 1000)
