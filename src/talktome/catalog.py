"""Message catalogue (design §4): templates per register, language and class; rendering. Stdlib only.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import re
import string
import tomllib
from functools import lru_cache
from importlib.resources import files
from typing import Any

SCHEMA = "talktome-catalog/1"
PLACEHOLDERS = frozenset({"name", "session", "his"})

# Removal of an empty {name} together with its comma, tried in order (one {name} per template at most).
_DROP_NAME: tuple[tuple[re.Pattern[str], bool], ...] = (
    (re.compile(r"^\{name\}\s*,\s*"), True),  # "{name}, X" → "X" (capitalize)
    (re.compile(r"\s*,\s*\{name\}(?=\s*,)"), False),  # "ready, {name}, X" → "ready, X"
    (re.compile(r"\s*,\s*\{name\}(?=\s*[.!?:;…])"), False),  # "Psst, {name}." → "Psst."
    (re.compile(r"\s*,\s*\{name\}\s*$"), False),
    (re.compile(r"\s*\{name\}"), False),
)


@lru_cache(maxsize=1)
def builtin() -> dict[str, Any]:
    data = tomllib.loads(files("talktome").joinpath("catalog.toml").read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"catalog schema must be {SCHEMA!r}")
    return data


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
    from .config import CLASSES, LANGUAGES, REGISTERS

    if not isinstance(templates, dict):
        return ["templates must be an object"]
    errors: list[str] = []
    for reg, by_lang in templates.items():
        if reg not in REGISTERS or not isinstance(by_lang, dict):
            errors.append(f"templates.{reg}: register must be one of {REGISTERS}")
            continue
        for lang, by_cls in by_lang.items():
            if lang not in LANGUAGES or not isinstance(by_cls, dict):
                errors.append(f"templates.{reg}.{lang}: language must be one of {LANGUAGES}")
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


def templates(cfg: dict[str, Any], register: str, lang: str, cls: str) -> list[str]:
    """The user's override if any, else the built-in list."""
    entry = cfg.get("templates", {}).get(register, {}).get(lang, {}).get(cls)
    if entry is not None:
        return [entry] if isinstance(entry, str) else list(entry)
    return list(builtin()[register][lang][cls])


def respell(text: str, mapping: dict[str, str]) -> str:
    """Pronunciation respellings applied to whole words before phonemization only (never to logged text)."""
    for word, spoken in mapping.items():
        text = re.sub(r"(?<!\w)%s(?!\w)" % re.escape(word), spoken, text)
    return text


def substitute(text: str, name: str, session: str, gender: str = "") -> str:
    """Fill {name}, {session} and {his} (his / her); an empty name goes with its comma. Other braces stay."""
    from .gender import pronoun

    capitalize = False
    if not name.strip():
        for pattern, cap in _DROP_NAME:
            text, n = pattern.subn("", text, count=1)
            if n:
                capitalize = cap
                break
    text = (
        text.replace("{name}", name.strip()).replace("{session}", session).replace("{his}", pronoun(gender))
    )
    text = re.sub(r"\s{2,}", " ", text).strip()
    if capitalize and text:
        text = text[0].upper() + text[1:]
    return text
