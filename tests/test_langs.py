"""Language packs (design §9): structure, defaults, voices, installation, rendering in every language.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from talktome import catalog, cli, config, gender, langs
from talktome.decide import Event, decide
from talktome.state import SessionState


def test_defaults() -> None:
    assert set(langs.codes()) == {"en", "fr", "es", "pt", "it", "hi", "zh"}
    assert [c for c in langs.codes() if langs.pack(c)["default"]] == sorted(langs.DEFAULT_LANGUAGES)
    assert config.defaults()["languages"] == list(langs.DEFAULT_LANGUAGES)
    assert {c for c in langs.codes() if langs.pack(c)["status"] == "experimental"} == {"hi", "zh"}
    assert (
        "ja" not in langs.codes()
    )  # Kokoro's phonemizer reads kanji as "Japanese letter" (2026-10-06 probe)


@pytest.mark.parametrize("code", langs.codes())
def test_pack_structure(code: str) -> None:
    p = langs.pack(code)
    assert p["engine"] == "kokoro" and p["kokoro"]["lang"]
    v = p["voices"]
    for g in config.GENDERS:
        assert config._VOICE.match(v[g])
        for name in v[f"pool_{g}"]:
            assert name[1] == g, f"{name} is not a {g} voice"  # bf_, em_, …
    if code != "fr":  # French has a single, female voice for everyone (D-0014)
        assert v["f"][1] == "f" and v["m"][1] == "m"
    for key in ("fallback_session", "discreet_session"):
        assert langs.word(code, key)
    for cls in catalog.CLASSES:
        assert catalog.builtin(code, "useful", cls)


@pytest.mark.parametrize("code", langs.codes())
@pytest.mark.parametrize("cls_event", ["help", "landed"])
def test_an_alert_in_every_language(code: str, cls_event: str, cfg: dict[str, Any]) -> None:
    c = {**cfg, "language": code}
    e = (
        Event(kind="pretool", tool_name="AskUserQuestion", cwd="/w/Merlin")
        if cls_event == "help"
        else Event(kind="stop", cwd="/w/Merlin")
    )
    u = decide(e, SessionState(turn_start=0.0), c, 100.0, random.Random(0)).utterance
    assert u is not None and u.lang == code and "Merlin" in u.text and "Ada" in u.text
    assert u.voice == langs.voice(code, "m")  # Merlin is a known male name


@pytest.mark.parametrize("code", langs.codes())
def test_discreet_in_every_language(code: str, cfg: dict[str, Any]) -> None:
    c = {**cfg, "language": code}
    e = Event(kind="pretool", tool_name="AskUserQuestion", cwd="/w/Acme")
    u = decide(e, SessionState(mode="discreet"), c, 100.0, random.Random(0)).utterance
    alias = langs.word(code, "discreet_session")
    assert u is not None and "Acme" not in u.text and alias.lower() in u.text.lower()


@pytest.mark.parametrize(
    "name, lang, expected",
    [
        ("la casa", "es", "f"),
        ("el motor", "es", "m"),
        ("a casa", "pt", "f"),
        ("o motor", "pt", "m"),
        ("lo stagista", "it", "m"),
        ("la macchina", "it", "f"),
        ("canción", "es", "f"),
        ("cidade", "pt", "f"),
        ("a session", "en", "f"),
    ],
)
def test_gender_cues_per_language(name: str, lang: str, expected: str) -> None:
    assert gender.guess(name, lang)[0] == expected


def test_language_must_be_installed(cfg: dict[str, Any]) -> None:
    c = {**cfg, "languages": ["en", "fr"]}
    with pytest.raises(config.ConfigError):
        config.set_value(c, "language", "es")
    assert config.set_value(c, "languages", '["en", "fr", "es"]')["languages"] == ["en", "fr", "es"]
    with pytest.raises(config.ConfigError):
        config.set_value(c, "languages", '["en", "ja"]')


def test_lang_command(capsys: pytest.CaptureFixture[str]) -> None:
    cli.main(["setup", "--no-link"])
    capsys.readouterr()
    assert cli.main(["lang"]) == 0
    listing = capsys.readouterr().out
    assert "en  speaking" in listing and "zh  installed" in listing and "(experimental)" in listing
    assert cli.main(["lang", "remove", "es"]) == 0 and "es" not in config.load()["languages"]
    assert cli.main(["set", "language", "es"]) == 2
    assert cli.main(["lang", "add", "es"]) == 0 and "es" in config.load()["languages"]
    assert cli.main(["set", "language", "es"]) == 0
    assert cli.main(["lang", "remove", "es"]) == 2  # the language in use
    assert cli.main(["lang", "add", "xx"]) == 2


def test_old_configuration_still_loads(cfg: dict[str, Any]) -> None:
    """A file written by 0.2.0: voices and speed for en/fr only, no `languages` key."""
    old = {
        **cfg,
        "voices": {"en": {"f": "bf_emma", "m": "bm_george"}, "fr": "ff_siwis"},
        "speed": {"en": 1.2, "fr": 1.0},
    }
    assert config.validate(old) == []
    assert config.voice_for(old, "es", "f") == "ef_dora" and config.speed_for(old, "es") == 1.0
