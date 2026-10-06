"""T6 (live, opt-in): Kokoro renders English and French; the pitch shift keeps the duration and moves f0.

Run with TALKTOME_LIVE=1 and TALKTOME_MODELS_DIR=<directory with the Kokoro model files>. Nothing is played.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from talktome import engine

pytestmark = pytest.mark.skipif(
    os.environ.get("TALKTOME_LIVE") != "1" or not os.environ.get("TALKTOME_MODELS_DIR"),
    reason="live test: set TALKTOME_LIVE=1 and TALKTOME_MODELS_DIR",
)


@pytest.fixture(scope="module")
def kokoro() -> engine.Kokoro:
    return engine.Kokoro(Path(os.environ["TALKTOME_MODELS_DIR"]))


def f0_median(y: np.ndarray, sr: int = engine.SR) -> float:
    """Frame autocorrelation: 40 ms frames, 10 ms hop, 70–400 Hz, voiced if peak > 0.5 and above −35 dB."""
    n, h = int(0.040 * sr), int(0.010 * sr)
    frames = np.lib.stride_tricks.sliding_window_view(y, n)[::h]
    rms = np.sqrt((frames**2).mean(axis=1)) + 1e-12
    db = 20 * np.log10(rms / rms.max())
    lo, hi = int(sr / 400), int(sr / 70)
    f0 = []
    for f, d in zip(frames, db):
        if d < -35:
            continue
        f = f - f.mean()
        ac = np.correlate(f, f, "full")[n - 1 :]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] > 0.5:
            f0.append(sr / lag)
    return float(np.median(f0))


@pytest.mark.parametrize(
    "voice, text",
    [("bm_george", "The results of Alpha landed."), ("ff_siwis", "Les résultats de Alpha sont déposés.")],
)
def test_renders(kokoro: engine.Kokoro, voice: str, text: str) -> None:
    y = kokoro.synth(text, voice, 1.0, 0.0)
    assert 1.0 < len(y) / engine.SR < 6.0 and float(np.max(np.abs(y))) > 0.05


def test_blend_renders(kokoro: engine.Kokoro) -> None:
    y = kokoro.synth("The results of Alpha landed.", "bm_george:0.7+bm_fable:0.3", 1.0, 0.0)
    assert len(y) > engine.SR


@pytest.mark.parametrize("semitones", [-2.0, 2.0])
def test_pitch_shift_keeps_duration_and_moves_f0(kokoro: engine.Kokoro, semitones: float) -> None:
    text = "Hi Ada, the results of Alpha landed."
    y0 = kokoro.synth(text, "bm_george", 1.0, 0.0)
    y1 = kokoro.synth(text, "bm_george", 1.0, semitones)
    assert len(y1) / len(y0) == pytest.approx(1.0, rel=0.05)
    assert f0_median(y1) / f0_median(y0) == pytest.approx(engine.shift_factor(semitones), rel=0.04)
