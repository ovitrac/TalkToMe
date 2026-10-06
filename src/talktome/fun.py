"""Jokes, surprising facts and `why` (design §7.1). Stdlib only.

`pick()` deals jokes and facts from a shuffled deck: none repeats before all have been told.
`why()` answers in the spirit of MATLAB's `why`: a random, grammatical, useless answer; the same seed gives
the same answer.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import json
import random
import tomllib
from functools import lru_cache
from importlib.resources import files
from typing import Any

from . import catalog, paths, state

SCHEMA = "talktome-fun/1"
KINDS = ("joke", "fact")
SPECIAL_SHARE = 0.2


@lru_cache(maxsize=1)
def data() -> dict[str, Any]:
    d = tomllib.loads(files("talktome").joinpath("fun.toml").read_text(encoding="utf-8"))
    if d.get("schema") != SCHEMA:
        raise ValueError(f"fun schema must be {SCHEMA!r}")
    return d


def items(kind: str, lang: str) -> list[str]:
    return list(data()[kind][lang])


def next_index(remaining: list[int], n: int, rng: random.Random) -> tuple[int, list[int]]:
    """Draw from the indices not told yet; an empty (or stale) deck is refilled."""
    pool = [i for i in remaining if 0 <= i < n] or list(range(n))
    idx = rng.choice(pool)
    pool.remove(idx)
    return idx, pool


def pick(kind: str, lang: str, rng: random.Random) -> str:
    """The next joke or fact in `lang`; the deck is kept in the state directory, across sessions."""
    pool = items(kind, lang)
    deck_file = paths.state_dir() / "fun.json"
    with state.locked("_fun"):
        try:
            decks = json.loads(deck_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            decks = {}
        key = f"{kind}.{lang}"
        idx, decks[key] = next_index(decks.get(key, []), len(pool), rng)
        paths.write_json_atomic(deck_file, decks)
    return pool[idx]


def _np_fr(w: dict[str, Any], rng: random.Random) -> str:
    noun, g = rng.choice(w["nouns"])
    adj = rng.choice(w["adjectives"])[0 if g == "m" else 1]
    return f"{'la' if g == 'f' else 'le'} {noun} {adj}"


def why(lang: str, rng: random.Random) -> str:
    """A random answer to "why?"."""
    w = data()["why"][lang]
    if rng.random() < SPECIAL_SHARE:
        return str(rng.choice(w["special"]))
    form = rng.randrange(3)
    if lang == "fr":
        subject = rng.choice(w["names"]) if rng.random() < 0.5 else _np_fr(w, rng)
        if form == 0:
            text = f"Parce que {subject} l'a {rng.choice(w['verbs'])}."
        elif form == 1:
            text = f"Pour {rng.choice(w['goals'])} {_np_fr(w, rng)}."
        else:
            text = f"{subject} me l'a demandé."
        text = catalog.elide_fr(text)
    else:

        def np() -> str:
            return f"the {rng.choice(w['adjectives'])} {rng.choice(w['nouns'])}"

        subject = rng.choice(w["names"]) if rng.random() < 0.5 else np()
        if form == 0:
            text = f"Because {subject} {rng.choice(w['verbs'])} it."
        elif form == 1:
            text = f"To {rng.choice(w['goals'])} {np()}."
        else:
            text = f"{subject} told me to."
    return text[0].upper() + text[1:]
