"""User directories (XDG) and atomic JSON writes. Standard library only.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

APP = "talktome"


def _xdg(var: str, default: str) -> Path:
    base = os.environ.get(var) or str(Path.home() / default)
    return Path(base) / APP


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config")


def state_dir() -> Path:
    return _xdg("XDG_STATE_HOME", ".local/state")


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache")


def data_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share")


def config_file() -> Path:
    return config_dir() / "config.json"


def log_file() -> Path:
    return state_dir() / "log.jsonl"


def write_json_atomic(path: Path, obj: Any) -> None:
    """Write JSON to a temporary file in the same directory, then rename it over `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
