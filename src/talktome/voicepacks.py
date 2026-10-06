"""Piper voices of downloadable language packs (design §7.3): fetch, verify, locate. Stdlib only.

Each voice is two files, the ONNX model and its JSON configuration, pinned in the pack by size and SHA-256
and fetched from a fixed revision of the voice repository. A download goes to a `.part` file and is renamed
only once verified; nothing unverified is ever used. The Piper engine itself (`piper-tts`, GPL-3.0) is an
optional dependency installed by the user (`pipx inject talktome piper-tts`); it is never vendored.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import importlib.util
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import langs, models, paths

INSTALL_HINT = (
    "pipx inject talktome piper-tts   (or, in a virtual environment: pip install 'talktome[piper]')"
)


def engine_available() -> bool:
    return importlib.util.find_spec("piper") is not None


def voice_dir() -> Path:
    return paths.data_dir() / "piper"


def voices(code: str) -> dict[str, dict[str, Any]]:
    return dict(langs.pack(code).get("piper", {}).get("voices", {}))


def files(code: str) -> list[tuple[str, Path, int, str]]:
    """(url, destination, size, sha256) of every file of the pack's voices."""
    base = langs.pack(code)["piper"]["base_url"]
    out = []
    for name, v in voices(code).items():
        for ext, key in ((".onnx", "onnx"), (".onnx.json", "json")):
            out.append(
                (base + v["path"] + ext, voice_dir() / f"{name}{ext}", int(v[key]["size"]), v[key]["sha256"])
            )
    return out


def download_size(code: str) -> int:
    return sum(size for _, _, size, _ in files(code))


def missing(code: str) -> list[tuple[str, Path, int, str]]:
    return [f for f in files(code) if not (f[1].is_file() and f[1].stat().st_size == f[2])]


def verify(code: str) -> list[str]:
    """Full check (reads every voice file): present, pinned size and SHA-256."""
    errors = []
    for _, dest, size, sha in files(code):
        if not dest.is_file():
            errors.append(f"missing {dest.name}")
        elif dest.stat().st_size != size or models.sha256(dest) != sha:
            errors.append(f"{dest.name}: size or SHA-256 differs from the pinned value")
    return errors


def fetch_file(url: str, dest: Path, size: int, sha256: str) -> None:
    """Download `url` to `dest` through a `.part` file; refuse anything that is not the pinned file."""
    import urllib.request  # network only here, on an explicit `talktome lang add`

    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    try:
        urllib.request.urlretrieve(url, part)  # noqa: S310 — https URL pinned in the pack
        if part.stat().st_size != size or models.sha256(part) != sha256:
            raise models.ModelError(f"{dest.name}: size or SHA-256 differs from the pinned value")
        os.replace(part, dest)
    finally:
        part.unlink(missing_ok=True)


def download(code: str, progress: Callable[[str], None] = print) -> list[str]:
    done = []
    for url, dest, size, sha in missing(code):
        progress(
            f"downloading {dest.name} ({f'{size / 1e6:.0f} MB' if size >= 1e6 else f'{size / 1e3:.0f} kB'}) …"
        )
        fetch_file(url, dest, size, sha)
        done.append(dest.name)
    return done


def remove(code: str) -> list[str]:
    removed = []
    for _, dest, _, _ in files(code):
        if dest.is_file():
            dest.unlink()
            removed.append(dest.name)
    return removed


def fingerprint(code: str, voice: str) -> str:
    """Identity of a downloaded voice for cache keys: full hash once, then trust (path, size, mtime)."""
    v = voices(code).get(voice)
    if v is None:
        raise models.ModelError(f"{voice} is not a voice of the {code} pack")
    record_file = paths.state_dir() / "piper.json"
    try:
        record = json.loads(record_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        record = {}
    stats = {}
    for ext, key in ((".onnx", "onnx"), (".onnx.json", "json")):
        p = voice_dir() / f"{voice}{ext}"
        try:
            st = p.stat()
        except OSError as e:
            raise models.ModelError(f"{p.name} missing — run `talktome lang add {code}`") from e
        stats[ext] = [str(p.resolve()), st.st_size, st.st_mtime_ns]
        if record.get(voice, {}).get(ext) != stats[ext] and models.sha256(p) != v[key]["sha256"]:
            raise models.ModelError(f"{p.name}: SHA-256 differs from the pinned value")
    if record.get(voice) != stats:
        record[voice] = stats
        paths.write_json_atomic(record_file, record)
    return f"piper:{voice}:{v['onnx']['sha256'][:12]}:{length_floor(code, voice)}"


def length_floor(code: str, voice: str) -> float:
    """The voice's measured duration floor, in length-scale units (engine.length_scale)."""
    return float(voices(code)[voice].get("length_floor", 0.0))


def paths_of(voice: str) -> tuple[Path, Path]:
    return voice_dir() / f"{voice}.onnx", voice_dir() / f"{voice}.onnx.json"
