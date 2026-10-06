"""Per-session state (turn start, last alerts, given name, rotation) in small JSON files. Stdlib only.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import fcntl
import json
import re
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import paths


@dataclass(frozen=True)
class SessionState:
    turn_start: float | None = None
    last_alert: float | None = None
    last_spoken: float | None = None
    last_say: float | None = None
    name: str | None = None
    variants: dict[str, int] = field(default_factory=dict)


def session_key(session_id: str) -> str:
    """A file-safe key for a session id (untrusted input)."""
    key = re.sub(r"[^A-Za-z0-9_-]", "_", session_id or "")[:64]
    return key or "unknown"


def _path(session_id: str) -> Path:
    return paths.state_dir() / "sessions" / f"{session_key(session_id)}.json"


def load(session_id: str) -> SessionState:
    try:
        raw = json.loads(_path(session_id).read_text(encoding="utf-8"))
        known = {k: raw[k] for k in SessionState.__dataclass_fields__ if k in raw}
        return SessionState(**known)
    except (OSError, ValueError, TypeError):
        return SessionState()


def save(session_id: str, st: SessionState) -> None:
    paths.write_json_atomic(_path(session_id), asdict(st))


@contextmanager
def locked(session_id: str) -> Generator[None, None, None]:
    """Serialize read-modify-write cycles on one session's state across processes."""
    lock = _path(session_id).with_suffix(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
