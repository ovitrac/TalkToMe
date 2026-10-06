"""Append-only JSON-lines log of utterances and suppressed alerts (design §3.4). Standard library only.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from . import paths


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def append(record: dict[str, Any]) -> None:
    p = paths.log_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"ts": now_iso(), **record}, ensure_ascii=False)
    with open(p, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def tail(n: int = 5) -> list[dict[str, Any]]:
    try:
        lines = paths.log_file().read_text(encoding="utf-8").splitlines()[-n:]
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out
