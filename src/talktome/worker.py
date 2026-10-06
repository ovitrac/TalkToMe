"""Speech worker (design §2): cross-process lock → audio cache → synthesis → playback → log.

Run detached by `spawn()` as `python -m talktome.worker '<utterance json>'`. Never raises to its caller:
every outcome, failures included, ends as one log line.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import catalog, config, journal, models, paths, player
from .decide import Utterance

LOCK_TIMEOUT_S = 90.0
CACHE_VERSION = 1


@contextmanager
def speaker_lock(timeout: float = LOCK_TIMEOUT_S) -> Generator[bool, None, None]:
    """One voice at a time across all sessions; yields False if the queue did not clear in time."""
    p = paths.state_dir() / "speak.lock"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    yield False
                    return
                time.sleep(0.05)
        try:
            yield True
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def cache_key(u: Utterance, spoken_text: str, model_id: str, volume: float) -> str:
    fields = {
        "v": CACHE_VERSION,
        "text": spoken_text,
        "voice": u.voice,
        "speed": round(u.speed, 4),
        "pitch": round(u.pitch_st, 3),
        "earcon": u.mood if u.earcon else None,
        "volume": round(volume, 3),
        "model": model_id,
    }
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode("utf-8")).hexdigest()[:32]


def render(u: Utterance, cfg: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    """Path of the WAV for `u`, from the cache or freshly synthesized; raises on any engine failure."""
    models_dir = models.resolve_dir(cfg)
    if models_dir is None:
        raise models.ModelError("no model directory configured (talktome setup)")
    model_id = models.fingerprint(models_dir)
    spoken = catalog.respell(u.text, cfg["respell"])
    path = paths.cache_dir() / f"{cache_key(u, spoken, model_id, float(cfg['volume']))}.wav"
    info: dict[str, Any] = {"engine": "kokoro", "model": model_id, "spoken_text": spoken}
    if path.is_file():
        return path, {**info, "cache": "hit", "synth_s": 0.0}
    import numpy as np
    import soundfile as sf

    from . import earcon, engine, moods

    t0 = time.monotonic()
    y = engine.Kokoro(models_dir).synth(spoken, u.voice, u.speed, u.pitch_st)
    if u.earcon:
        y = earcon.with_speech(earcon.render(moods.get(u.mood)), y)
    y = y * float(cfg["volume"])
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    if peak > 0.99:
        y = y * (0.99 / peak)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part.wav")
    sf.write(tmp, y, engine.SR, subtype="PCM_16")
    os.replace(tmp, path)
    return path, {**info, "cache": "miss", "synth_s": round(time.monotonic() - t0, 3)}


def speak(u: Utterance, cfg: dict[str, Any], lock_timeout: float = LOCK_TIMEOUT_S) -> dict[str, Any]:
    """Speak `u` now (blocking); returns the log record, which is also appended to the log."""
    rec: dict[str, Any] = {**asdict(u), "outcome": None}
    t0 = time.monotonic()
    try:
        with speaker_lock(lock_timeout) as acquired:
            rec["wait_s"] = round(time.monotonic() - t0, 3)
            if not acquired:
                rec["outcome"] = "dropped: queue timeout"
                return rec
            try:
                path, info = render(u, cfg)
                rec.update(info)
            except Exception as e:  # engine or models unavailable: fallback voice
                rec["engine_error"] = f"{type(e).__name__}: {e}"
                t1 = time.monotonic()
                player.spd_say(catalog.respell(u.text, cfg["respell"]), u.lang)
                rec.update(engine="spd-say", play_s=round(time.monotonic() - t1, 3), outcome="spoken")
                return rec
            t1 = time.monotonic()
            rec["player"] = player.play(path, cfg["player"])
            rec["play_s"] = round(time.monotonic() - t1, 3)
            rec["outcome"] = "played"
    except Exception as e:
        rec["outcome"] = f"error: {type(e).__name__}: {e}"
    finally:
        rec["total_s"] = round(time.monotonic() - t0, 3)
        try:
            journal.append(rec)
        except OSError:
            pass
    return rec


def spawn(u: Utterance) -> None:
    """Start a detached worker for `u` and return at once."""
    subprocess.Popen(
        [sys.executable, "-m", "talktome.worker", u.to_json()],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        u = Utterance.from_json(args[0])
        cfg = config.load()
    except Exception as e:
        try:
            journal.append({"outcome": f"error: worker input: {type(e).__name__}: {e}"})
        except OSError:
            pass
        return 0
    speak(u, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
