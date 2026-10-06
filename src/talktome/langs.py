"""Language packs (design §9): one TOML file per language under `talktome/lang/`. Stdlib only.

A pack holds the alert templates, jokes, facts, `why` word lists, voices and grammar of one language.
The packs listed in the configuration (`languages`) are installed; the others are available. A pack is
parsed only when its language is used, which keeps the hook fast.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import re
from functools import lru_cache
from importlib.resources import files
from typing import Any

SCHEMA = "talktome-lang/1"
DEFAULT_LANGUAGES = ("en", "fr", "es", "pt", "it", "hi", "zh")  # installed by default (lead, 2026-10-06)
LANG_BY_PREFIX = {"a": "en-us", "b": "en-gb"}
VOWELS = "aeiouàâäáéèêëíîïóôöúùûüãõAEIOUÀÂÄÁÉÈÊËÍÎÏÓÔÖÚÙÛÜÃÕ"


def _dir() -> Any:
    return files("talktome").joinpath("lang")


@lru_cache(maxsize=1)
def codes() -> tuple[str, ...]:
    """Every available language (installed or not), from the pack file names."""
    return tuple(sorted(p.name[:-5] for p in _dir().iterdir() if p.name.endswith(".toml")))


@lru_cache(maxsize=None)
def pack(code: str) -> dict[str, Any]:
    if code not in codes():
        raise KeyError(f"no language pack {code!r} (available: {', '.join(codes())})")
    import tomllib  # only when a pack is read: keeps the hook's import path short

    d = tomllib.loads(_dir().joinpath(f"{code}.toml").read_text(encoding="utf-8"))
    if d.get("schema") != SCHEMA or d.get("code") != code:
        raise ValueError(f"lang/{code}.toml: schema must be {SCHEMA!r} and code {code!r}")
    return d


def engine(code: str) -> str:
    """`kokoro` (built in) or `piper` (voices downloaded by `talktome lang add`, design §7.3)."""
    return str(pack(code).get("engine", "kokoro"))


def kokoro_lang(code: str, voice: str) -> str:
    """Phonemizer language for Kokoro; English follows the voice (a* en-us, b* en-gb)."""
    k = str(pack(code)["kokoro"]["lang"])
    return LANG_BY_PREFIX.get(voice[:1], "en-us") if k == "voice" else k


def voice(code: str, gender: str) -> str:
    return str(pack(code)["voices"][gender])


def pool(code: str, gender: str) -> list[str]:
    return list(pack(code)["voices"].get(f"pool_{gender}", []))


def distinct_voices(code: str) -> int:
    v = pack(code)["voices"]
    return len({v["f"], v["m"], *v.get("pool_f", []), *v.get("pool_m", [])})


def voice_prefixes(code: str) -> set[str]:
    v = pack(code)["voices"]
    return {x[0] for x in (v["f"], v["m"], *v.get("pool_f", []), *v.get("pool_m", []))}


def word(code: str, key: str) -> str:
    return str(pack(code)["words"][key])


def his(code: str, gender: str) -> str:
    return str(pack(code)["words"]["his"].get(gender, "their"))


def grammar(code: str) -> dict[str, Any]:
    return dict(pack(code).get("grammar", {}))


@lru_cache(maxsize=None)
def _elision(code: str) -> tuple[re.Pattern[str], dict[str, str]] | None:
    rules = {w.lower(): r for w, r in grammar(code).get("elision", [])}
    if not rules:
        return None
    words = "|".join(re.escape(w) for w in sorted(rules, key=len, reverse=True))
    return re.compile(rf"\b({words}) (?=[{VOWELS}])", re.IGNORECASE), rules


def polish(code: str, text: str) -> str:
    """The pack's contractions (es: a el → al), then its elisions before a vowel (fr: de Atlas → d'Atlas)."""
    for a, b in grammar(code).get("contractions", []):
        text = text.replace(a, b)
    el = _elision(code)
    if el is None:
        return text
    pattern, rules = el

    def repl(m: re.Match[str]) -> str:
        w = m.group(1)
        out = rules[w.lower()]
        return out[0].upper() + out[1:] if w[0].isupper() else out

    return pattern.sub(repl, text)
