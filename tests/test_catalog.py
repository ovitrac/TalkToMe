"""T2 — the catalogue is complete and renders cleanly with and without a name (design §10).

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from talktome import catalog, config

ALL = [
    (reg, lang, cls, t)
    for reg in config.REGISTERS
    for lang in config.LANGUAGES
    for cls in config.CLASSES
    for t in catalog.builtin()[reg][lang][cls]
]
DEFECTS = re.compile(r"[{}]|\s[,.!?:;]\s*[,.!?:;]|,\s*[.!?]|^\W|\s{2}|,,")


@pytest.mark.parametrize("reg", config.REGISTERS)
@pytest.mark.parametrize("lang", config.LANGUAGES)
@pytest.mark.parametrize("cls", config.CLASSES)
def test_catalogue_is_complete(reg: str, lang: str, cls: str) -> None:
    pool = catalog.builtin()[reg][lang][cls]
    assert len(pool) == (1 if reg == "useful" else 5)
    assert len(set(pool)) == len(pool)


@pytest.mark.parametrize("reg, lang, cls, template", ALL)
def test_template_is_valid(reg: str, lang: str, cls: str, template: str) -> None:
    assert catalog.check_template(template) == []


@pytest.mark.parametrize("lang", config.LANGUAGES)
@pytest.mark.parametrize("cls", config.CLASSES)
def test_useful_is_one_sentence(lang: str, cls: str) -> None:
    (t,) = catalog.builtin()["useful"][lang][cls]
    assert len(re.findall(r"[.!?]", t)) == 1 and t.rstrip().endswith((".", "!", "?"))


@pytest.mark.parametrize("name", ["Ada", ""])
@pytest.mark.parametrize("reg, lang, cls, template", ALL)
def test_render_is_clean(reg: str, lang: str, cls: str, template: str, name: str) -> None:
    text = catalog.substitute(template, name, "Alpha")
    assert "Alpha" in text
    assert ("Ada" in text) == bool(name)
    # French typography puts a space before ! ? : ; — allowed; anything else is a defect.
    probe = re.sub(r" (?=[!?:;])", "", text) if lang == "fr" else text
    assert not DEFECTS.search(probe), text
    assert text[0].isupper(), text


@pytest.mark.parametrize(
    "template, expected",
    [
        ("{name}, the results of {session} landed.", "The results of Alpha landed."),
        (
            "Psst, {name}. {session} has a question only you can answer.",
            "Psst. Alpha has a question only you can answer.",
        ),
        (
            "Whenever you're ready, {name}, {session} is listening.",
            "Whenever you're ready, Alpha is listening.",
        ),
        ("Bonne nouvelle, {name} : {session} a terminé.", "Bonne nouvelle : Alpha a terminé."),
        ("Toc toc, {name} ! {session} attend ton feu vert.", "Toc toc ! Alpha attend ton feu vert."),
        ("{session} est tout ouïe, {name}.", "Alpha est tout ouïe."),
    ],
)
def test_empty_name_removal(template: str, expected: str) -> None:
    assert catalog.substitute(template, "", "Alpha") == expected


def test_free_text_keeps_other_braces() -> None:
    assert catalog.substitute("{name}, {x} on {session}", "Ada", "Alpha") == "Ada, {x} on Alpha"


def test_user_override(cfg: dict[str, Any]) -> None:
    cfg["templates"] = {"useful": {"en": {"help": "{session} wants you."}}}
    assert catalog.templates(cfg, "useful", "en", "help") == ["{session} wants you."]
    assert catalog.templates(cfg, "useful", "fr", "help") == catalog.builtin()["useful"]["fr"]["help"]
