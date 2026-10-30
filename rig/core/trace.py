import itertools
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ..util.logging import get_logger

logger = get_logger()


class TraceEvent(BaseModel):
    kind: str
    run_id: str
    ts: float
    seq: int
    fields: dict[str, Any]


class NullTrace:
    """A trace that records nothing: for library callers and tests that don't want a file."""

    def log_event(self, kind: str, **fields: Any) -> None:
        pass


class Trace:
    def __init__(self, run_id: str, filepath: str) -> None:
        self.run_id = run_id
        path = Path(filepath).resolve()
        if not path.exists():
            logger.debug(f"Creating trace file: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)
        self.f = open(filepath, "a")  # noqa: SIM115
        self.seq = itertools.count()

    def __del__(self) -> None:
        self.f.close()

    def log_event(self, kind: str, **fields: Any) -> None:
        try:
            event = TraceEvent(
                kind=kind, run_id=self.run_id, ts=time.time(), seq=next(self.seq), fields=fields
            )
            self.f.write(event.model_dump_json() + "\n")
            self.f.flush()
        except Exception as err:
            logger.exception(f"Error logging event trace \n{err}")

    @staticmethod
    def get_dummy_trace(run_id: str | None = None) -> Trace:
        from datetime import datetime

        ts_prefix = datetime.now().strftime("%Y%m%d%--%H:%M:%S")
        import uuid

        _run_id = run_id or str(uuid.uuid4())
        return Trace(
            run_id=_run_id, filepath=str(Path.cwd() / "traces" / f"{ts_prefix}-{_run_id}.jsonl")
        )


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    trace = Trace.get_dummy_trace()
    trace.log_event(kind="test", value="aditya")
