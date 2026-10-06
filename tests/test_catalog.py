"""T2 — every language pack is complete and renders cleanly with and without a name (design §4, §9).

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from talktome import catalog, langs

LATIN = ("en", "fr", "es", "pt", "it")
ALL = [
    (reg, lang, cls, t)
    for reg in catalog.REGISTERS
    for lang in langs.codes()
    for cls in catalog.CLASSES
    for t in catalog.builtin(lang, reg, cls)
]
END = re.compile(r"[.!?।。！？]")
DEFECTS = re.compile(r"[{}]|\s[,.!?:;]\s*[,.!?:;]|,\s*[.!?]|^\W|\s{2}|,,")


def stable(lang: str) -> bool:
    return bool(langs.pack(lang)["status"] == "stable")


@pytest.mark.parametrize("reg", catalog.REGISTERS)
@pytest.mark.parametrize("lang", langs.codes())
@pytest.mark.parametrize("cls", catalog.CLASSES)
def test_catalogue_is_complete(reg: str, lang: str, cls: str) -> None:
    pool = catalog.builtin(lang, reg, cls)
    expected = 1 if reg == "useful" else (5 if stable(lang) else 2)
    assert len(pool) == expected and len(set(pool)) == len(pool)


@pytest.mark.parametrize("reg, lang, cls, template", ALL)
def test_template_is_valid(reg: str, lang: str, cls: str, template: str) -> None:
    assert catalog.check_template(template) == []


@pytest.mark.parametrize("lang", langs.codes())
@pytest.mark.parametrize("cls", catalog.CLASSES)
def test_useful_is_one_sentence(lang: str, cls: str) -> None:
    (t,) = catalog.builtin(lang, "useful", cls)
    assert len(END.findall(t)) == 1 and END.match(t.rstrip()[-1])


@pytest.mark.parametrize("name", ["Ada", ""])
@pytest.mark.parametrize("reg, lang, cls, template", ALL)
def test_render_is_clean(reg: str, lang: str, cls: str, template: str, name: str) -> None:
    text = catalog.substitute(template, name, "Alpha", "f", lang)
    assert "Alpha" in text and "{" not in text and "}" not in text
    assert ("Ada" in text) == bool(name)
    if lang in LATIN:
        # French puts a space before ! ? : ; and Spanish opens with ¡ ¿ — allowed; anything else is a defect.
        probe = re.sub(r" (?=[!?:;])", "", text) if lang == "fr" else text
        probe = probe.lstrip("¡¿")
        assert not DEFECTS.search(probe), text
        assert probe[0].isupper(), text
    else:
        assert not re.search(r"^[,，。！？：]|[,，][,，]|\s{2}", text), text


@pytest.mark.parametrize(
    "template, lang, expected",
    [
        ("{name}, the results of {session} landed.", "en", "The results of Alpha landed."),
        (
            "Psst, {name}. {session} has a question only you can answer.",
            "en",
            "Psst. Alpha has a question only you can answer.",
        ),
        (
            "Whenever you're ready, {name}, {session} is listening.",
            "en",
            "Whenever you're ready, Alpha is listening.",
        ),
        ("Bonne nouvelle, {name} : {session} a terminé.", "fr", "Bonne nouvelle : Alpha a terminé."),
        ("Toc toc, {name} ! {session} attend ton feu vert.", "fr", "Toc toc ! Alpha attend ton feu vert."),
        ("{session} est tout ouïe, {name}.", "fr", "Alpha est tout ouïe."),
        ("¡Tachán! {session} ha cumplido, {name}.", "es", "¡Tachán! Alpha ha cumplido."),
        ("{name}，{session}需要你的帮助。", "zh", "Alpha需要你的帮助。"),
        ("{session}举手了，{name}，需要帮忙。", "zh", "Alpha举手了，需要帮忙。"),
        ("{session} के नतीजे तैयार हैं, {name}।", "hi", "Alpha के नतीजे तैयार हैं।"),
    ],
)
def test_empty_name_removal(template: str, lang: str, expected: str) -> None:
    assert catalog.substitute(template, "", "Alpha", "f", lang) == expected


def test_free_text_keeps_other_braces() -> None:
    assert catalog.substitute("{name}, {x} on {session}", "Ada", "Alpha") == "Ada, {x} on Alpha"


def test_user_override(cfg: dict[str, Any]) -> None:
    cfg["templates"] = {"useful": {"en": {"help": "{session} wants you."}}}
    assert catalog.templates(cfg, "useful", "en", "help") == ["{session} wants you."]
    assert catalog.templates(cfg, "useful", "fr", "help") == catalog.builtin("fr", "useful", "help")
