"""Per-session modes (design §5.2): on, discreet, off; set in the session, at launch, or by a folder rule.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pytest

from talktome import cli, config, hook, journal, state, worker
from talktome.decide import Event, Utterance, decide, session_mode
from talktome.state import SessionState

CWD = "/work/clients/acme/app"


def ev(kind: str, **kw: Any) -> Event:
    return Event(kind=kind, session_id="s-1", cwd=CWD, **kw)


def run(e: Event, st: SessionState, cfg: dict[str, Any], now: float = 1000.0) -> Any:
    return decide(e, st, cfg, now, random.Random(0))


ASK = {"tool_name": "AskUserQuestion"}


# --- where the mode comes from -----------------------------------------------------------------------


def test_default_is_on(cfg: dict[str, Any]) -> None:
    assert session_mode(ev("pretool"), SessionState(), cfg) == ("on", "default")


def test_precedence(cfg: dict[str, Any]) -> None:
    c = {**cfg, "private": {"/work/clients/*": "off"}}
    assert session_mode(ev("pretool"), SessionState(), c) == ("off", "folder rule /work/clients/*")
    assert session_mode(ev("pretool", session_mode="discreet"), SessionState(), c)[0] == "discreet"
    assert session_mode(ev("pretool", session_mode="discreet"), SessionState(mode="on"), c)[0] == "on"


def test_folder_rule_matches_subfolders_only_under_the_pattern(cfg: dict[str, Any]) -> None:
    c = {**cfg, "private": {"/work/clients/acme": "discreet"}}
    assert session_mode(ev("pretool"), SessionState(), c)[0] == "discreet"  # /work/clients/acme/app
    other = Event(kind="pretool", cwd="/work/internal/tool")
    assert session_mode(other, SessionState(), c)[0] == "on"


def test_folder_rule_expands_home(cfg: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", "/home/ada")
    c = {**cfg, "private": {"~/clients/*": "off"}}
    assert session_mode(Event(kind="stop", cwd="/home/ada/clients/x/y"), SessionState(), c)[0] == "off"


def test_unknown_launch_value_is_ignored(cfg: dict[str, Any]) -> None:
    assert session_mode(ev("pretool", session_mode="loud"), SessionState(), cfg)[0] == "on"


# --- what each mode does -------------------------------------------------------------------------------


def test_off_is_silent_and_closes_the_turn(cfg: dict[str, Any]) -> None:
    st = SessionState(mode="off", turn_start=0.0)
    assert run(ev("pretool", **ASK), st, cfg).reason == "session off"
    d = run(ev("stop"), st, cfg, 500.0)
    assert d.utterance is None and d.state.turn_start is None
    assert run(ev("fun", text="A joke."), st, cfg).utterance is None


@pytest.mark.parametrize(
    "lang, expected",
    [("en", "Ada, a session needs your help."), ("fr", "Ada, une session a besoin de ton aide.")],
)
def test_discreet_hides_the_name(lang: str, expected: str, cfg: dict[str, Any]) -> None:
    u: Utterance = run(
        ev("pretool", **ASK), SessionState(mode="discreet", name="Acme audit"), {**cfg, "language": lang}
    ).utterance
    assert u.text == expected and u.session != "Acme audit" and u.mode == "discreet"


def test_discreet_landed_in_french_elides(cfg: dict[str, Any]) -> None:
    c = {**cfg, "language": "fr"}
    u = run(ev("stop"), SessionState(mode="discreet", turn_start=0.0), c, 500.0).utterance
    assert u.text == "Ada, les résultats d'une session sont déposés."


def test_discreet_refuses_free_text_but_allows_canned(cfg: dict[str, Any]) -> None:
    st = SessionState(mode="discreet")
    assert (
        run(ev("say", text="The Acme audit is done."), st, cfg).reason == "discreet session: free text is off"
    )
    assert run(ev("fun", text="Why not?", cls="why"), st, cfg).utterance is not None


def test_discreet_voice_does_not_depend_on_the_session(cfg: dict[str, Any]) -> None:
    c = {**cfg, "register": "fun"}
    voices = {
        run(
            Event(kind="pretool", tool_name="AskUserQuestion", cwd=f"/w/{n}"),
            SessionState(mode="discreet"),
            c,
        ).utterance.voice
        for n in ("Hermes", "Ariadne", "alpha", "beta")
    }
    assert len(voices) == 1


def test_test_event_plays_even_when_off(cfg: dict[str, Any]) -> None:
    assert run(ev("test", cls="landed"), SessionState(mode="off"), cfg).utterance is not None


# --- hook and command line ---------------------------------------------------------------------------------


@pytest.fixture
def spawned(monkeypatch: pytest.MonkeyPatch) -> list[Utterance]:
    out: list[Utterance] = []
    monkeypatch.setattr(worker, "spawn", out.append)
    return out


def test_hook_reads_talktome_at_launch(spawned: list[Utterance]) -> None:
    cli.main(["setup", "--name", "Ada", "--no-link"])
    raw = json.dumps(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "AskUserQuestion",
            "session_id": "h1",
            "cwd": "/w/acme",
        }
    )
    assert hook.run(raw, {"TALKTOME": "off"}) == "session off" and spawned == []
    assert journal.tail(1)[0] == {
        **journal.tail(1)[0],
        "outcome": "suppressed: session off",
        "session_id": "h1",
    }
    assert "acme" not in str(journal.tail(1)[0])


def test_cli_mode(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    cli.main(["setup", "--no-link"])
    assert cli.main(["mode", "off"]) == 2  # outside a Claude Code session
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "m1")
    assert cli.main(["mode", "discreet"]) == 0 and state.load("m1").mode == "discreet"
    assert "discreet (set in the session)" in capsys.readouterr().out
    assert cli.main(["mode", "auto"]) == 0 and state.load("m1").mode is None


def test_private_config_is_validated(cfg: dict[str, Any], tmp_path: Path) -> None:
    assert config.set_value(cfg, "private", '{"~/clients/*": "discreet"}')["private"] == {
        "~/clients/*": "discreet"
    }
    with pytest.raises(config.ConfigError):
        config.set_value(cfg, "private", '{"~/clients/*": "quiet"}')
