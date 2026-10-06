"""Command line: settings, mute, session name, and the guards of `say`.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import json
import time

import pytest

from talktome import cli, config, journal, state, worker
from talktome.decide import Utterance


@pytest.fixture
def spawned(monkeypatch: pytest.MonkeyPatch) -> list[Utterance]:
    out: list[Utterance] = []
    monkeypatch.setattr(worker, "spawn", out.append)
    return out


@pytest.fixture
def configured() -> None:
    assert cli.main(["setup", "--name", "Ada", "--no-link"]) == 0


def test_setup_creates_config() -> None:
    assert cli.main(["setup", "--name", "Ada", "--language", "fr", "--no-link"]) == 0
    c = config.load()
    assert (c["name"], c["language"]) == ("Ada", "fr")


def test_set_and_show(configured: None, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["set", "voices.en", "bf_emma"]) == 0
    assert cli.main(["set", "register", "fun"]) == 0
    assert cli.main(["set", "language", "de"]) == 2
    capsys.readouterr()
    assert cli.main(["show"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["voices"]["en"] == "bf_emma" and shown["register"] == "fun" and shown["language"] == "en"


def test_mute_unmute(configured: None) -> None:
    assert cli.main(["mute", "10"]) == 0
    assert config.load()["mute_until"] == pytest.approx(time.time() + 600, abs=5)
    assert cli.main(["mute"]) == 0 and config.load()["mute"] is True
    assert cli.main(["unmute"]) == 0
    c = config.load()
    assert c["mute"] is False and c["mute_until"] is None


def test_name_requires_a_session(monkeypatch: pytest.MonkeyPatch) -> None:
    assert cli.main(["name", "Data", "cleaning"]) == 2
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "abc-123")
    assert cli.main(["name", "Data", "cleaning"]) == 0
    assert state.load("abc-123").name == "Data cleaning"


def test_say_spawns_rendered_text(
    configured: None, spawned: list[Utterance], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "abc-123")
    monkeypatch.setenv("TALKTOME_SESSION", "Pipeline")
    assert cli.main(["say", "--mood", "sorry", "Hi {name}, tests are red on {session}."]) == 0
    (u,) = spawned
    assert (u.text, u.mood, u.session_id) == ("Hi Ada, tests are red on Pipeline.", "sorry", "abc-123")
    assert state.load("abc-123").last_say is not None


@pytest.mark.parametrize("text", ["x" * 281, "The key is TAG-9f3a2b1c, keep it safe."])
def test_say_refuses(configured: None, spawned: list[Utterance], text: str) -> None:
    assert cli.main(["say", text]) == 2 and spawned == []


def test_say_requires_setup(spawned: list[Utterance]) -> None:
    assert cli.main(["say", "Hello."]) == 2 and spawned == []


def test_say_when_muted_is_logged_not_spoken(configured: None, spawned: list[Utterance]) -> None:
    cli.main(["mute"])
    assert cli.main(["say", "Hello."]) == 0 and spawned == []
    assert journal.tail(1)[0]["outcome"] == "suppressed: muted"
