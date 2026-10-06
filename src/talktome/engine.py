"""Speech synthesis with Kokoro-82M through kokoro-onnx; pitch shift without speed change (design §5).

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from .config import parse_voice

SR = 24000
LANG_BY_PREFIX = {"a": "en-us", "b": "en-gb", "f": "fr-fr"}
SPEED_RANGE = (0.5, 2.0)


def lang_for(voice_spec: str) -> str:
    """Kokoro language code from the first voice of a spec (a* en-us, b* en-gb, f* fr-fr)."""
    return LANG_BY_PREFIX.get(parse_voice(voice_spec)[0][0][0], "en-us")


def shift_factor(semitones: float) -> float:
    return float(2.0 ** (semitones / 12.0))


def pitch_shift(y: npt.NDArray[np.float32], semitones: float) -> npt.NDArray[np.float32]:
    """Resample by 2^(p/12): pitch moves by p semitones and duration shrinks by the same factor."""
    if semitones == 0 or len(y) < 2:
        return y
    n = max(2, int(round(len(y) / shift_factor(semitones))))
    x = np.linspace(0.0, len(y) - 1, n)
    return np.interp(x, np.arange(len(y)), y).astype(np.float32)


def synth_speed(speed: float, semitones: float) -> float:
    """Kokoro speed that, after `pitch_shift`, gives back `speed` (clamped to Kokoro's range)."""
    lo, hi = SPEED_RANGE
    return min(hi, max(lo, speed / shift_factor(semitones)))


class Kokoro:
    def __init__(self, models_dir: Path) -> None:
        from kokoro_onnx import Kokoro as _Kokoro

        self.k = _Kokoro(str(models_dir / "kokoro-v1.0.onnx"), str(models_dir / "voices-v1.0.bin"))

    def voices(self) -> list[str]:
        return sorted(self.k.get_voices())

    def _style(self, voice_spec: str) -> Any:
        parts = parse_voice(voice_spec)
        if len(parts) == 1:
            return parts[0][0]
        total = sum(w for _, w in parts)
        return sum(self.k.get_voice_style(name) * (w / total) for name, w in parts)

    def synth(self, text: str, voice_spec: str, speed: float, pitch_st: float) -> npt.NDArray[np.float32]:
        y, sr = self.k.create(
            text, voice=self._style(voice_spec), speed=synth_speed(speed, pitch_st), lang=lang_for(voice_spec)
        )
        if sr != SR:
            raise RuntimeError(f"unexpected sample rate {sr}")
        return pitch_shift(np.asarray(y, dtype=np.float32), pitch_st)
