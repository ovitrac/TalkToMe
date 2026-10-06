"""Message catalogue (design §4): templates per register, language and class; rendering. Stdlib only.

The templates live in the language packs (`langs`); the user may override any list in the configuration.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import re
import string
from typing import Any

from . import langs

PLACEHOLDERS = frozenset({"name", "session", "his"})
CLASSES = ("help", "attention", "input", "landed")
REGISTERS = ("useful", "fun")

# Removal of an empty {name} together with its comma, tried in order (one {name} per template at most);
# ASCII and full-width commas, Latin, Devanagari (।) and CJK (。！？：) punctuation.
_DROP_NAME: tuple[tuple[re.Pattern[str], bool], ...] = (
    (re.compile(r"^\{name\}\s*[,，]\s*"), True),  # "{name}, X" → "X" (capitalize)
    (re.compile(r"\s*[,，]\s*\{name\}(?=\s*[,，])"), False),  # "ready, {name}, X" → "ready, X"
    (re.compile(r"\s*[,，]\s*\{name\}(?=\s*[.!?:;…।。！？：])"), False),  # "Psst, {name}." → "Psst."
    (re.compile(r"\s*[,，]\s*\{name\}\s*$"), False),
    (re.compile(r"\s*\{name\}"), False),
)


def fields(template: str) -> list[str]:
    return [f for _, f, _, _ in string.Formatter().parse(template) if f is not None]


def check_template(template: str) -> list[str]:
    """Errors for one alert template: known placeholders only, {session} present, {name} at most once."""
    try:
        fs = fields(template)
    except ValueError as e:
        return [f"{template!r}: {e}"]
    errors = [f"{template!r}: unknown placeholder {{{f}}}" for f in fs if f not in PLACEHOLDERS]
    if "session" not in fs:
        errors.append(f"{template!r}: {{session}} is required")
    if fs.count("name") > 1:
        errors.append(f"{template!r}: {{name}} may appear once")
    return errors


def validate_overrides(templates: Any) -> list[str]:
    if not isinstance(templates, dict):
        return ["templates must be an object"]
    errors: list[str] = []
    for reg, by_lang in templates.items():
        if reg not in REGISTERS or not isinstance(by_lang, dict):
            errors.append(f"templates.{reg}: register must be one of {REGISTERS}")
            continue
        for lang, by_cls in by_lang.items():
            if lang not in langs.codes() or not isinstance(by_cls, dict):
                errors.append(f"templates.{reg}.{lang}: language must be one of {langs.codes()}")
                continue
            for cls, entry in by_cls.items():
                where = f"templates.{reg}.{lang}.{cls}"
                items = [entry] if isinstance(entry, str) else entry
                if cls not in CLASSES:
                    errors.append(f"{where}: class must be one of {CLASSES}")
                elif not isinstance(items, list) or not items or not all(isinstance(t, str) for t in items):
                    errors.append(f"{where}: a template or a non-empty list of templates")
                else:
                    errors.extend(f"{where}: {x}" for t in items for x in check_template(t))
    return errors


def builtin(lang: str, register: str, cls: str) -> list[str]:
    return list(langs.pack(lang)["templates"][register][cls])


def templates(cfg: dict[str, Any], register: str, lang: str, cls: str) -> list[str]:
    """The user's override if any, else the language pack's list."""
    entry = cfg.get("templates", {}).get(register, {}).get(lang, {}).get(cls)
    if entry is not None:
        return [entry] if isinstance(entry, str) else list(entry)
    return builtin(lang, register, cls)


def elide_fr(text: str) -> str:
    """French elision before a vowel: le/la → l', de → d', que → qu' (les résultats d'Atlas, parce qu'Ada)."""
    return langs.polish("fr", text)


def respell(text: str, mapping: dict[str, str]) -> str:
    """Pronunciation respellings applied to whole words before phonemization only (never to logged text)."""
    for word, spoken in mapping.items():
        text = re.sub(r"(?<!\w)%s(?!\w)" % re.escape(word), spoken, text)
    return text


def substitute(text: str, name: str, session: str, gender: str = "", lang: str = "en") -> str:
    """Fill {name}, {session} and {his} (his / her, from the pack); an empty name goes with its comma.
    Other braces stay as they are."""
    capitalize = False
    if not name.strip():
        for pattern, cap in _DROP_NAME:
            text, n = pattern.subn("", text, count=1)
            if n:
                capitalize = cap
                break
    possessive = langs.his(lang, gender) if gender else "their"
    text = text.replace("{name}", name.strip()).replace("{session}", session).replace("{his}", possessive)
    text = re.sub(r"\s{2,}", " ", text).strip()
    if text and (capitalize or text[0].islower()):
        text = (
            text[0].upper() + text[1:]
        )  # a sentence starts with a capital ("a session needs…" → "A session…")
    return text
