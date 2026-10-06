"""Speech synthesis: Kokoro-82M (kokoro-onnx) built in, Piper for downloadable packs (design §5, §7.3).

Both engines return float32 audio at `SR`, pitch-shifted without speed change, so earcons, volume and the
cache work the same for every language.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from .config import parse_voice

SR = 24000
SPEED_RANGE = (0.5, 2.0)


def shift_factor(semitones: float) -> float:
    return float(2.0 ** (semitones / 12.0))


def pitch_shift(y: npt.NDArray[np.float32], semitones: float) -> npt.NDArray[np.float32]:
    """Resample by 2^(p/12): pitch moves by p semitones and duration shrinks by the same factor."""
    if semitones == 0 or len(y) < 2:
        return y
    n = max(2, int(round(len(y) / shift_factor(semitones))))
    x = np.linspace(0.0, len(y) - 1, n)
    return np.interp(x, np.arange(len(y)), y).astype(np.float32)


def resample(y: npt.NDArray[np.float32], sr: int, target: int = SR) -> npt.NDArray[np.float32]:
    """Linear resampling to `target` Hz (Piper voices are 16 or 22.05 kHz; speech bandwidth is kept)."""
    if sr == target or len(y) < 2:
        return y
    n = max(2, int(round(len(y) * target / sr)))
    x = np.linspace(0.0, len(y) - 1, n)
    return np.interp(x, np.arange(len(y)), y).astype(np.float32)


def synth_speed(speed: float, semitones: float) -> float:
    """Engine speed that, after `pitch_shift`, gives back `speed` (clamped to Kokoro's range)."""
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

    def synth(
        self, text: str, voice_spec: str, speed: float, pitch_st: float, lang: str
    ) -> npt.NDArray[np.float32]:
        """`lang` is the phonemizer code (langs.kokoro_lang): en-us, en-gb, fr-fr, es, pt-br, it, hi, cmn."""
        y, sr = self.k.create(
            text, voice=self._style(voice_spec), speed=synth_speed(speed, pitch_st), lang=lang
        )
        if sr != SR:
            raise RuntimeError(f"unexpected sample rate {sr}")
        return pitch_shift(np.asarray(y, dtype=np.float32), pitch_st)


MIN_LENGTH_SCALE = 0.2


def recompose(phonemes: list[str], id_map: Mapping[str, Any]) -> list[str]:
    """Piper decomposes phonemes (NFD: ç → c + U+0327); a voice that knows only `ç` would lose the mark."""
    out: list[str] = []
    for ph in phonemes:
        if out and unicodedata.combining(ph) and ph not in id_map:
            merged = unicodedata.normalize("NFC", out[-1] + ph)
            if merged in id_map:
                out[-1] = merged
                continue
        out.append(ph)
    return out


def length_scale(base: float, floor: float, speed: float) -> float:
    """Piper length scale for `speed`. Durations go as D(ls) ≈ b·(ls + floor): each phoneme is rounded up
    to whole frames, a share that does not scale. D(ls)/D(base) = 1/speed gives (base + floor)/speed − floor.
    """
    return max(MIN_LENGTH_SCALE, (base + floor) / speed - floor)


class Piper:
    """A downloaded Piper voice (`piper-tts`, GPL-3.0, optional: installed by the user, never vendored).

    `floor` is the voice's measured duration floor (design §7.3). Sampling noise varies renderings slightly.
    """

    def __init__(self, model: Path, config: Path, floor: float = 0.0) -> None:
        from piper import PiperVoice

        self.v = PiperVoice.load(model, config_path=config)
        self.floor = floor
        id_map, phonemize = self.v.config.phoneme_id_map, self.v.phonemize
        recomposed = lambda text: [recompose(s, id_map) for s in phonemize(text)]  # noqa: E731
        self.v.phonemize = recomposed  # type: ignore[method-assign]

    def synth(self, text: str, speed: float, pitch_st: float) -> npt.NDArray[np.float32]:
        from piper import SynthesisConfig

        ls = length_scale(float(self.v.config.length_scale), self.floor, synth_speed(speed, pitch_st))
        chunks = list(self.v.synthesize(text, syn_config=SynthesisConfig(length_scale=ls)))
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        y = np.concatenate([np.asarray(c.audio_float_array, dtype=np.float32) for c in chunks])
        return pitch_shift(resample(y, int(chunks[0].sample_rate)), pitch_st)
