"""Earcons: short synthesized chimes that announce a message and carry its mood (design §5).

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from .moods import Mood

SR = 24000
GAP_S = 0.12


def render(mood: Mood, sr: int = SR, peak: float = 0.3) -> npt.NDArray[np.float32]:
    """Additive tones (3 harmonics) with a 5 ms attack and an exponential decay, summed and normalized."""
    total = max(start + dur for _, start, dur in mood.earcon) + 0.05
    out = np.zeros(int(round(total * sr)), dtype=np.float64)
    for midi, start, dur in mood.earcon:
        f0 = 440.0 * 2.0 ** ((midi - 69) / 12.0)
        n = int(round(dur * sr))
        t = np.arange(n) / sr
        tone = sum((0.5 ** (k - 1)) * np.sin(2 * np.pi * k * f0 * t) for k in (1, 2, 3))
        env = np.minimum(1.0, t / 0.005) * np.exp(-6.9 * t / dur)
        i = int(round(start * sr))
        out[i : i + n] += tone * env
    m = float(np.max(np.abs(out)))
    if m > 0:
        out *= peak / m
    return out.astype(np.float32)


def with_speech(
    chime: npt.NDArray[np.float32], speech: npt.NDArray[np.float32], sr: int = SR
) -> npt.NDArray[np.float32]:
    return np.concatenate([chime, np.zeros(int(GAP_S * sr), dtype=np.float32), speech])
