"""Kokoro model files: location, SHA-256 verification, cheap fingerprint, explicit fetch. Stdlib only.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

from . import paths

FILES = {
    "kokoro-v1.0.onnx": "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5",
    "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}
BASE_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"


class ModelError(Exception):
    pass


def default_dir() -> Path:
    return paths.data_dir() / "models"


def resolve_dir(cfg: dict[str, Any]) -> Path | None:
    """The configured directory, else the default one if it holds the files, else None."""
    if cfg.get("models_dir"):
        return Path(cfg["models_dir"]).expanduser()
    d = default_dir()
    return d if all((d / f).is_file() for f in FILES) else None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(models_dir: Path) -> list[str]:
    """Full check (reads 338 MB): every file present with its published SHA-256."""
    errors = []
    for name, digest in FILES.items():
        p = models_dir / name
        if not p.is_file():
            errors.append(f"missing {p}")
        elif sha256(p) != digest:
            errors.append(f"SHA-256 mismatch for {p}")
    return errors


def fingerprint(models_dir: Path) -> str:
    """Model identity for cache keys: full hash once, then trust (path, size, mtime) until they change."""
    record_file = paths.state_dir() / "models.json"
    stats = {}
    for name in FILES:
        p = models_dir / name
        try:
            st = p.stat()
        except OSError as e:
            raise ModelError(f"missing {p}") from e
        stats[name] = [str(p.resolve()), st.st_size, st.st_mtime_ns]
    try:
        record = json.loads(record_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        record = {}
    if record.get("stats") != stats:
        errors = verify(models_dir)
        if errors:
            raise ModelError("; ".join(errors))
        record = {"stats": stats}
        paths.write_json_atomic(record_file, record)
    return "kokoro-v1.0:" + FILES["kokoro-v1.0.onnx"][:12] + FILES["voices-v1.0.bin"][:12]


def fetch(dest: Path) -> list[str]:
    """Download the model files into `dest` and verify them (explicit network use: `setup --fetch`)."""
    dest.mkdir(parents=True, exist_ok=True)
    done = []
    for name, digest in FILES.items():
        target = dest / name
        if target.is_file() and sha256(target) == digest:
            continue
        tmp = target.with_suffix(target.suffix + ".part")
        urllib.request.urlretrieve(BASE_URL + name, tmp)  # noqa: S310 — fixed https URL
        if sha256(tmp) != digest:
            tmp.unlink(missing_ok=True)
            raise ModelError(f"downloaded {name} does not match its SHA-256")
        os.replace(tmp, target)
        done.append(name)
    return done
