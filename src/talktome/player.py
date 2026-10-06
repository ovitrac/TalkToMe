"""Audio playback through the first available system player. Standard library only.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

COMMANDS: dict[str, list[str]] = {
    "pw-play": ["pw-play"],
    "paplay": ["paplay"],
    "aplay": ["aplay", "-q"],
    "ffplay": ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
    "mpv": ["mpv", "--no-video", "--really-quiet"],
}


class PlayerError(Exception):
    pass


def find(pref: str = "auto") -> list[str] | None:
    """argv prefix of the preferred player, the first available one for "auto", or an absolute path."""
    if pref.startswith("/"):
        return [pref] if os.access(pref, os.X_OK) else None
    names = list(COMMANDS) if pref == "auto" else [pref]
    for name in names:
        if name in COMMANDS and shutil.which(name):
            return COMMANDS[name]
    return None


def play(path: Path, pref: str = "auto", timeout: float = 60.0) -> str:
    argv = find(pref)
    if argv is None:
        raise PlayerError(f"no audio player found (preference {pref!r})")
    r = subprocess.run(
        [*argv, str(path)],
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if r.returncode != 0:
        raise PlayerError(
            f"{argv[0]} exited {r.returncode}: {r.stderr.decode(errors='replace').strip()[:200]}"
        )
    return argv[0]


def spd_say(text: str, lang: str, timeout: float = 60.0) -> None:
    """Fallback voice (speech-dispatcher) when Kokoro or its model files are unavailable."""
    if not shutil.which("spd-say"):
        raise PlayerError("no fallback voice (spd-say not found)")
    subprocess.run(
        ["spd-say", "-w", "-l", lang[:2], text],
        check=True,
        timeout=timeout,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
