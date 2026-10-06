"""Session gender (design §5.1): the guess, the voice it selects, his/her agreement, and the overrides.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import random
import re
from typing import Any

import pytest

from talktome import catalog, cli, config, gender, state
from talktome.decide import Event, decide, session_gender
from talktome.state import SessionState

# --- the guess --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Hermes", "m"),
        ("Hermès", "m"),
        ("Ariadne", "f"),
        ("Rosetta", "f"),
        ("Agnès", "f"),
        ("Étienne", "m"),
        ("la chaise", "f"),
        ("le moteur", "m"),
        ("une table", "f"),
        ("un pipeline", "m"),
        ("les données", "f"),
        ("des moteurs", "m"),
        ("nation", "f"),
        ("maison", "f"),
        ("fromage", "m"),
        ("système", "m"),
        ("chaise", "f"),
        ("Bruno", "m"),
        ("moteur", "m"),
    ],
)
def test_guess(name: str, expected: str) -> None:
    assert gender.guess(name)[0] == expected


@pytest.mark.parametrize("name", ["ETL2", "API", "x9", "2026", "Origami", "", "   "])
def test_improvised_names_are_stable(name: str) -> None:
    g, reason = gender.guess(name)
    assert g in config.GENDERS and "improvised" in reason
    assert all(gender.guess(name) == (g, reason) for _ in range(5))


def test_improvisation_uses_both_genders() -> None:
    assert {gender.guess(f"P{i}Q")[0] for i in range(40)} == {"f", "m"}


def test_pronoun() -> None:
    assert (gender.pronoun("m"), gender.pronoun("f"), gender.pronoun("")) == ("his", "her", "their")


# --- catalogue: people, not objects -------------------------------------------------------------------------


def test_no_session_is_called_it() -> None:
    for reg in config.REGISTERS:
        for cls in config.CLASSES:
            for t in catalog.builtin()[reg]["en"][cls]:
                assert not re.search(r"\b(it|its)\b", t, re.IGNORECASE), t


@pytest.mark.parametrize("sex, word", [("m", "his"), ("f", "her")])
def test_his_her(sex: str, word: str) -> None:
    t = "{session} has landed {his} work on your desk, {name}."
    assert catalog.substitute(t, "Ada", "Hermes", sex) == f"Hermes has landed {word} work on your desk, Ada."


# --- voices -------------------------------------------------------------------------------------------------


def ev(name: str) -> Event:
    return Event(kind="stop", session_id=name, cwd=f"/w/{name}")


def speak(e: Event, cfg: dict[str, Any], st: SessionState | None = None) -> Any:
    return decide(e, st or SessionState(turn_start=0.0), cfg, 100.0, random.Random(0)).utterance


@pytest.mark.parametrize("register", config.REGISTERS)
@pytest.mark.parametrize(
    "name, sex", [("Hermes", "m"), ("Ariadne", "f"), ("la chaise", "f"), ("le moteur", "m")]
)
def test_english_voice_follows_gender(register: str, name: str, sex: str, cfg: dict[str, Any]) -> None:
    u = speak(ev(name), {**cfg, "register": register})
    assert u.gender == sex and u.voice[1] == sex  # bf_/af_ female, bm_/am_ male


@pytest.mark.parametrize("register", config.REGISTERS)
@pytest.mark.parametrize("name", ["Hermes", "Ariadne"])
def test_french_keeps_its_single_voice(register: str, name: str, cfg: dict[str, Any]) -> None:
    u = speak(ev(name), {**cfg, "register": register, "language": "fr"})
    assert u.voice == "ff_siwis"


def test_one_voice_for_both_genders_is_honoured(cfg: dict[str, Any]) -> None:
    c = {**cfg, "voices": {"en": "bm_lewis", "fr": "ff_siwis"}}
    assert speak(ev("Ariadne"), c).voice == "bm_lewis" and speak(ev("Hermes"), c).voice == "bm_lewis"


def test_fun_pool_without_the_gender_falls_back(cfg: dict[str, Any]) -> None:
    c = {
        **cfg,
        "register": "fun",
        "fun": {"voice_pool": ["bm_george", "am_michael"], "voice_per_session": True},
    }
    assert speak(ev("Ariadne"), c).voice == "bf_emma"


# --- overrides: session state, then the user's map, then the guess ----------------------------------------


def test_override_order(cfg: dict[str, Any]) -> None:
    assert session_gender(SessionState(), cfg, "Hermes") == "m"
    assert session_gender(SessionState(), {**cfg, "genders": {"Hermes": "f"}}, "Hermes") == "f"
    assert session_gender(SessionState(gender="m"), {**cfg, "genders": {"Hermes": "f"}}, "Hermes") == "m"


def test_state_gender_changes_voice_and_pronoun(cfg: dict[str, Any]) -> None:
    c = {**cfg, "register": "fun"}
    u = speak(
        Event(kind="say", session_id="s", cwd="/w/Hermes", text="{session} lost {his} keys."),
        c,
        SessionState(gender="f"),
    )
    assert u.text == "Hermes lost her keys." and u.voice[1] == "f"


# --- configuration and command line -----------------------------------------------------------------------


def test_voices_per_gender_config(cfg: dict[str, Any]) -> None:
    c = config.set_value({**cfg, "voices": {"en": "bm_george", "fr": "ff_siwis"}}, "voices.en.f", "af_heart")
    assert c["voices"]["en"] == {"f": "af_heart", "m": "bm_george"}
    assert config.voice_for(c, "en", "f") == "af_heart" and config.voice_for(c, "fr", "m") == "ff_siwis"
    with pytest.raises(config.ConfigError):
        config.set_value(c, "voices.en", '{"f": "af_heart"}')
    with pytest.raises(config.ConfigError):
        config.set_value(c, "genders", '{"Hermes": "x"}')
    assert config.set_value(c, "genders", '{"Hermes": "f"}')["genders"] == {"Hermes": "f"}


def test_cli_name_and_gender(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    cli.main(["setup", "--no-link"])
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "abc")
    assert cli.main(["name", "la", "chaise"]) == 0
    assert "she (article la)" in capsys.readouterr().out
    assert cli.main(["gender", "m"]) == 0 and state.load("abc").gender == "m"
    assert "he (set)" in capsys.readouterr().out
    assert cli.main(["gender", "auto"]) == 0 and state.load("abc").gender is None
    assert cli.main(["name", "Ariadne", "--gender", "m"]) == 0 and state.load("abc").gender == "m"
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID")
    assert cli.main(["gender", "f"]) == 2
