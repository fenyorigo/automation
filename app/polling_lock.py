from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator, TextIO


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK_FILE = ROOT / "logs" / "polling.lock"


class PollCycleBusy(RuntimeError):
    """Raised when another process already owns the polling-cycle lock."""


@contextmanager
def polling_cycle_lock(*, wait: bool = False, operation: str = "poll") -> Iterator[None]:
    path = Path(os.getenv("POLL_LOCK_FILE", str(DEFAULT_LOCK_FILE)))
    path.parent.mkdir(parents=True, exist_ok=True)
    handle: TextIO = path.open("a+", encoding="utf-8")
    try:
        try:
            flags = fcntl.LOCK_EX if wait else fcntl.LOCK_EX | fcntl.LOCK_NB
            fcntl.flock(handle.fileno(), flags)
        except BlockingIOError as error:
            raise PollCycleBusy("Már folyamatban van egy lekérdezési kör.") from error
        handle.seek(0)
        handle.truncate()
        handle.write(
            f"pid={os.getpid()} operation={operation} started_at="
            f"{datetime.now(UTC).isoformat(timespec='seconds')}\n"
        )
        handle.flush()
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
