"""Jokes, facts and why (design §7.1); French elision; macOS playback and fallback voice.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import random
import re

import pytest

from talktome import catalog, cli, config, fun, player, worker
from talktome.decide import Utterance

# --- content ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", fun.KINDS)
@pytest.mark.parametrize("lang", config.LANGUAGES)
def test_content(kind: str, lang: str) -> None:
    pool = fun.items(kind, lang)
    assert len(pool) >= 12 and len(set(pool)) == len(pool)
    for t in pool:
        assert len(t) <= 280 and not re.search(
            r"[{}]|\d", t
        ), t  # spoken as written: no digits, no placeholders


def test_both_languages_have_the_same_facts() -> None:
    assert len(fun.items("fact", "en")) == len(fun.items("fact", "fr"))


def test_deck_never_repeats_before_the_end() -> None:
    rng, remaining, seen = random.Random(3), [], []
    for _ in range(2 * 12):
        idx, remaining = fun.next_index(remaining, 12, rng)
        seen.append(idx)
    assert sorted(seen[:12]) == list(range(12)) and sorted(seen[12:]) == list(range(12))


def test_pick_persists_the_deck() -> None:
    told = [fun.pick("joke", "fr", random.Random(i)) for i in range(len(fun.items("joke", "fr")))]
    assert sorted(told) == sorted(fun.items("joke", "fr"))


# --- why -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("lang", config.LANGUAGES)
def test_why_is_reproducible_and_grammatical(lang: str) -> None:
    answers = [fun.why(lang, random.Random(seed)) for seed in range(300)]
    assert answers == [fun.why(lang, random.Random(seed)) for seed in range(300)]
    assert len(set(answers)) > 100
    for a in answers:
        assert a[0].isupper() and a.rstrip()[-1] in ".?!", a


def test_why_french_agreement_and_elision() -> None:
    answers = {fun.why("fr", random.Random(seed)) for seed in range(2000)}
    joined = " ".join(answers)
    assert "le architecte" not in joined and "la ingénieur" not in joined and "que A" not in joined
    assert not re.search(r"\b(le|la|de|que) [aeiouéèêàâîôû]", joined, re.IGNORECASE)
    assert re.search(
        r"\bla mathématicienne (ensommeillée|brillante|nerveuse|retraitée|survoltée|mystérieuse|"
        r"inquiète|généreuse|têtue|surmenée)\b",
        joined,
    )


# --- French elision ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("les résultats de Atlas", "les résultats d'Atlas"),
        ("Parce que Edsger l'a voulu.", "Parce qu'Edsger l'a voulu."),
        ("Pour épater le ingénieur nerveux.", "Pour épater l'ingénieur nerveux."),
        ("La architecte", "L'architecte"),
        ("les résultats de Merlin", "les résultats de Merlin"),
        ("de yaourt", "de yaourt"),
    ],
)
def test_elide_fr(text: str, expected: str) -> None:
    assert catalog.elide_fr(text) == expected


# --- commands --------------------------------------------------------------------------------------------


@pytest.fixture
def spawned(monkeypatch: pytest.MonkeyPatch) -> list[Utterance]:
    out: list[Utterance] = []
    monkeypatch.setattr(worker, "spawn", out.append)
    return out


@pytest.mark.parametrize(
    "cmd, mood", [(["joke"], "cheerful"), (["fact"], "warm"), (["why", "42"], "neutral")]
)
def test_fun_commands(
    cmd: list[str], mood: str, spawned: list[Utterance], capsys: pytest.CaptureFixture[str]
) -> None:
    cli.main(["setup", "--no-link", "--language", "fr"])
    capsys.readouterr()  # drop setup's own output
    assert cli.main(cmd) == 0
    (u,) = spawned
    assert u.mood == mood and u.lang == "fr" and u.cls == cmd[0] and u.text == capsys.readouterr().out.strip()


def test_why_seed_on_the_command_line(spawned: list[Utterance]) -> None:
    cli.main(["setup", "--no-link"])
    cli.main(["why", "7"])
    cli.main(["why", "7"])
    assert spawned[0].text == spawned[1].text == fun.why("en", random.Random(7))


# --- macOS ------------------------------------------------------------------------------------------------


def test_afplay_is_a_player(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(player.shutil, "which", lambda name: "/usr/bin/afplay" if name == "afplay" else None)
    assert player.find("auto") == ["afplay"]


def test_fallback_uses_macos_say(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(player.shutil, "which", lambda name: "/usr/bin/say" if name == "say" else None)
    monkeypatch.setattr(player.sys, "platform", "darwin")
    monkeypatch.setattr(player.subprocess, "run", lambda argv, **kw: calls.append(argv))
    assert player.fallback_speak("Hello.", "en") == "say" and calls == [["say", "Hello."]]
    monkeypatch.setattr(player.sys, "platform", "linux")
    with pytest.raises(player.PlayerError):
        player.fallback_speak("Hello.", "en")
