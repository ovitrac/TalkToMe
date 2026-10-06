"""T6 (live, opt-in): Kokoro renders every built-in language; the pitch shift keeps the duration and moves
f0; Piper renders the downloaded packs.

Run with TALKTOME_LIVE=1 and TALKTOME_MODELS_DIR=<directory with the Kokoro model files>; the Piper tests
also need `piper-tts` and the voices (TALKTOME_PIPER_DIR, default ~/.local/share/talktome/piper).
Nothing is played.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from talktome import engine, langs

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


@pytest.mark.parametrize("code", [c for c in langs.codes() if langs.engine(c) == "kokoro"])
def test_every_language_renders(kokoro: engine.Kokoro, code: str) -> None:
    from talktome import catalog

    voices = set(kokoro.voices())
    for g in ("f", "m"):
        assert langs.voice(code, g) in voices and set(langs.pool(code, g)) <= voices
    text = catalog.substitute(catalog.builtin(code, "useful", "landed")[0], "Ada", "Merlin", "m", code)
    v = langs.voice(code, "m")
    y = kokoro.synth(text, v, 1.0, 0.0, langs.kokoro_lang(code, v))
    assert 1.0 < len(y) / engine.SR < 8.0 and float(np.max(np.abs(y))) > 0.05


def test_blend_renders(kokoro: engine.Kokoro) -> None:
    y = kokoro.synth("The results of Alpha landed.", "bm_george:0.7+bm_fable:0.3", 1.0, 0.0, "en-gb")
    assert len(y) > engine.SR


@pytest.mark.parametrize("semitones", [-2.0, 2.0])
def test_pitch_shift_keeps_duration_and_moves_f0(kokoro: engine.Kokoro, semitones: float) -> None:
    text = "Hi Ada, the results of Alpha landed."
    y0 = kokoro.synth(text, "bm_george", 1.0, 0.0, "en-gb")
    y1 = kokoro.synth(text, "bm_george", 1.0, semitones, "en-gb")
    assert len(y1) / len(y0) == pytest.approx(1.0, rel=0.05)
    assert f0_median(y1) / f0_median(y0) == pytest.approx(engine.shift_factor(semitones), rel=0.04)


PIPER_DIR = Path(os.environ.get("TALKTOME_PIPER_DIR", "~/.local/share/talktome/piper")).expanduser()


@pytest.mark.parametrize("code", [c for c in langs.codes() if langs.engine(c) == "piper"])
@pytest.mark.parametrize("g", ["f", "m"])
def test_piper_renders(code: str, g: str) -> None:
    from talktome import catalog, voicepacks

    pytest.importorskip("piper")
    v = langs.voice(code, g)
    model, cfg = PIPER_DIR / f"{v}.onnx", PIPER_DIR / f"{v}.onnx.json"
    if not model.is_file():
        pytest.skip(f"{v} not downloaded (talktome lang add {code})")
    text = catalog.substitute(catalog.builtin(code, "useful", "landed")[0], "Ada", "Merlin", g, code)
    piper = engine.Piper(model, cfg, floor=voicepacks.length_floor(code, v))
    y = piper.synth(text, 1.0, 0.0)
    assert 1.0 < len(y) / engine.SR < 8.0 and float(np.max(np.abs(y))) > 0.05
    # Piper's duration noise spreads single renderings by ±5 % (2026-10-06): compare means of six
    normal = np.mean([len(piper.synth(text, 1.0, 0.0)) for _ in range(6)])
    fast = np.mean([len(piper.synth(text, 1.5, 0.0)) for _ in range(6)])
    assert fast / normal == pytest.approx(1 / 1.5, rel=0.10)
