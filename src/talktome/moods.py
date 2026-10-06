"""Mood presets (design §5): speed factor, pitch offset in semitones, earcon notes.

Kokoro has no emotion control, so a mood combines the levers that measurably act on the voice.
Earcon notes are (MIDI note, start in seconds, duration in seconds).

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mood:
    name: str
    speed: float
    pitch_st: float
    earcon: tuple[tuple[int, float, float], ...]


MOODS: dict[str, Mood] = {
    m.name: m
    for m in (
        Mood("neutral", 1.00, 0.0, ((76, 0.00, 0.35),)),
        Mood("warm", 0.95, 0.0, ((72, 0.00, 0.25), (76, 0.15, 0.35))),
        Mood("calm", 0.90, -1.0, ((60, 0.00, 0.60), (64, 0.00, 0.60), (67, 0.00, 0.60), (71, 0.00, 0.60))),
        Mood("cheerful", 1.05, 1.0, ((72, 0.00, 0.18), (76, 0.12, 0.18), (79, 0.24, 0.30))),
        Mood("firm", 1.05, 0.0, ((74, 0.00, 0.15), (74, 0.20, 0.20))),
        Mood("urgent", 1.12, 1.0, ((79, 0.00, 0.10), (79, 0.13, 0.10), (79, 0.26, 0.15))),
        Mood("sorry", 0.90, -2.0, ((76, 0.00, 0.25), (73, 0.20, 0.40))),
    )
}


def get(name: str) -> Mood:
    """Return the named mood, or `neutral` for an unknown name."""
    return MOODS.get(name, MOODS["neutral"])
