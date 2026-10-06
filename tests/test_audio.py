"""Pitch shift, speed compensation and earcons (design §5), without the Kokoro model.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import numpy as np
import pytest

from talktome import earcon, engine
from talktome.moods import MOODS


def zero_crossings(y: np.ndarray) -> int:
    return int(np.sum(np.abs(np.diff(np.signbit(y).astype(int)))))


@pytest.mark.parametrize("semitones", [-2.0, -1.0, 1.0, 2.0, 12.0])
def test_pitch_shift_moves_frequency_and_length(semitones: float) -> None:
    sr, f0 = engine.SR, 220.0
    y = np.sin(2 * np.pi * f0 * np.arange(sr) / sr).astype(np.float32)
    z = engine.pitch_shift(y, semitones)
    f = engine.shift_factor(semitones)
    assert len(z) == pytest.approx(len(y) / f, abs=1)
    measured = zero_crossings(z) / 2 / (len(z) / sr)
    assert measured == pytest.approx(f0 * f, rel=0.01)


def test_pitch_shift_zero_is_identity() -> None:
    y = np.ones(100, dtype=np.float32)
    assert engine.pitch_shift(y, 0.0) is y


@pytest.mark.parametrize("speed, semitones", [(1.0, 2.0), (0.9, -2.0), (1.12, 1.0)])
def test_synth_speed_compensates(speed: float, semitones: float) -> None:
    # synthesized at speed/f, then shortened by f: the net duration factor is that of `speed`.
    s = engine.synth_speed(speed, semitones)
    assert s * engine.shift_factor(semitones) == pytest.approx(speed)


def test_synth_speed_is_clamped() -> None:
    assert engine.synth_speed(0.5, 4.0) == 0.5 and engine.synth_speed(2.0, -4.0) == 2.0


def test_lang_for() -> None:
    assert engine.lang_for("bm_george") == "en-gb"
    assert engine.lang_for("af_heart") == "en-us"
    assert engine.lang_for("ff_siwis") == "fr-fr"
    assert engine.lang_for("bm_george:0.7+bm_fable:0.3") == "en-gb"


@pytest.mark.parametrize("mood", sorted(MOODS))
def test_earcon(mood: str) -> None:
    m = MOODS[mood]
    y = earcon.render(m)
    assert y.dtype == np.float32
    assert len(y) / earcon.SR == pytest.approx(max(s + d for _, s, d in m.earcon) + 0.05, abs=1e-3)
    assert float(np.max(np.abs(y))) == pytest.approx(0.3, rel=1e-6)
    joined = earcon.with_speech(y, np.ones(10, dtype=np.float32))
    assert len(joined) == len(y) + int(earcon.GAP_S * earcon.SR) + 10
