"""Jokes, surprising facts and `why` (design §7.1). Stdlib only.

`pick()` deals jokes and facts from a shuffled deck: none repeats before all have been told.
`why()` answers in the spirit of MATLAB's `why`: a random, grammatical, useless answer; the same seed gives
the same answer. The content and the sentence patterns come from the language packs.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import json
import random
from typing import Any

from . import langs, paths, state

KINDS = ("joke", "fact")
SPECIAL_SHARE = 0.2


def items(kind: str, lang: str) -> list[str]:
    return list(langs.pack(lang)[kind]["items"])


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


def _noun_phrase(w: dict[str, Any], rng: random.Random) -> str:
    """The pack's `np`: noun ([noun, gender] or plain), agreeing adjective ([m, f] or plain), article."""
    noun = rng.choice(w["nouns"])
    noun, g = (noun[0], noun[1]) if isinstance(noun, list) else (noun, "m")
    adj = rng.choice(w["adjectives"])
    adj = adj[0 if g == "m" else 1] if isinstance(adj, list) else adj
    art = w.get("articles", {}).get(g, "")
    return str(w["np"]).replace("{art}", art).replace("{noun}", noun).replace("{adj}", adj).strip()


def why(lang: str, rng: random.Random) -> str:
    """A random answer to "why?"; packs without patterns only have their special answers."""
    w = langs.pack(lang)["why"]
    patterns = w.get("patterns", [])
    if not patterns or rng.random() < SPECIAL_SHARE:
        return str(rng.choice(w["special"]))
    pattern = str(rng.choice(patterns))
    subject = rng.choice(w["names"]) if rng.random() < 0.5 else _noun_phrase(w, rng)
    text = (
        pattern.replace("{subject}", subject)
        .replace("{verb}", rng.choice(w["verbs"]))
        .replace("{goal}", rng.choice(w["goals"]))
        .replace("{np}", _noun_phrase(w, rng))
    )
    text = langs.polish(lang, text)
    return text[0].upper() + text[1:]
