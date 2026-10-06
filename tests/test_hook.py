"""T3 — the hook never interferes with a session, and maps hook payloads to events (design §3, §10).

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from talktome import cli, hook, journal, state, worker
from talktome.decide import Utterance

SID = "sess-1"


def payload(event: str, **kw: Any) -> str:
    return json.dumps({"hook_event_name": event, "session_id": SID, "cwd": "/w/alpha", **kw})


@pytest.fixture
def spawned(monkeypatch: pytest.MonkeyPatch) -> list[Utterance]:
    out: list[Utterance] = []
    monkeypatch.setattr(worker, "spawn", out.append)
    return out


@pytest.fixture
def configured() -> None:
    assert cli.main(["setup", "--name", "Ada", "--no-link"]) == 0


# --- payload → event ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, kind, detail",
    [
        (payload("UserPromptSubmit", prompt="x"), "prompt", ""),
        (payload("PreToolUse", tool_name="AskUserQuestion"), "pretool", "AskUserQuestion"),
        (payload("Notification", notification_type="permission_prompt"), "notification", "permission_prompt"),
        (
            payload("Notification", message="Claude needs your permission to use Bash"),
            "notification",
            "permission_prompt",
        ),
        (payload("Notification", message="Claude is waiting for your input"), "notification", "idle_prompt"),
        (payload("Stop", stop_hook_active=True), "stop", ""),
    ],
)
def test_event_from_payload(raw: str, kind: str, detail: str) -> None:
    ev = hook.event_from_payload(json.loads(raw), {"TALKTOME_SESSION": "Launch name"})
    assert ev is not None and ev.kind == kind and ev.session_id == SID and ev.session_name == "Launch name"
    assert detail in (ev.tool_name, ev.notification_type, "")
    assert ev.stop_hook_active == (kind == "stop")


@pytest.mark.parametrize("raw", ["", "   ", "{oops", "[1, 2]", "null", payload("SessionStart"), "{}"])
def test_junk_is_ignored(raw: str, configured: None, spawned: list[Utterance]) -> None:
    assert hook.run(raw, {}) in ("no input", "ignored event", "error")
    assert spawned == []


def test_unconfigured_is_silent(spawned: list[Utterance]) -> None:
    assert hook.run(payload("PreToolUse", tool_name="AskUserQuestion"), {}) == "not configured"
    assert spawned == []


# --- the sequence of a turn ---------------------------------------------------------------------------------


def test_long_turn_lands(configured: None, spawned: list[Utterance]) -> None:
    assert hook.run(payload("UserPromptSubmit", prompt="x"), {}, now=1000.0) == "turn start"
    assert hook.run(payload("Stop", stop_hook_active=False), {}, now=1061.0) == "spoken"
    (u,) = spawned
    assert (u.cls, u.text) == ("landed", "Ada, the results of alpha landed.")
    assert state.load(SID).turn_start is None


def test_short_turn_is_logged_not_spoken(configured: None, spawned: list[Utterance]) -> None:
    hook.run(payload("UserPromptSubmit", prompt="x"), {}, now=1000.0)
    assert hook.run(payload("Stop"), {}, now=1030.0) == "short turn"
    assert spawned == [] and journal.tail(1)[0]["outcome"] == "suppressed: short turn"


def test_question_then_permission_is_debounced(configured: None, spawned: list[Utterance]) -> None:
    assert hook.run(payload("PreToolUse", tool_name="AskUserQuestion"), {}, now=1000.0) == "spoken"
    assert (
        hook.run(payload("Notification", notification_type="permission_prompt"), {}, now=1005.0) == "debounce"
    )
    assert [u.cls for u in spawned] == ["help"]


def test_other_tools_are_ignored_silently(configured: None, spawned: list[Utterance]) -> None:
    assert hook.run(payload("PreToolUse", tool_name="Bash"), {}, now=1000.0) == "not an alert"
    assert spawned == [] and journal.tail(1) == []


# --- the real entry point, in a subprocess ----------------------------------------------------------------


def entry() -> list[str]:
    script = Path(sys.executable).parent / "talktome"
    return [str(script)] if script.exists() else [sys.executable, "-m", "talktome.cli"]


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "{oops",
        payload("UserPromptSubmit", prompt="x"),
        payload("PreToolUse", tool_name="AskUserQuestion"),
    ],
)
@pytest.mark.parametrize("setup", [False, True])
def test_entry_point_is_silent_and_exits_zero(raw: str, setup: bool) -> None:
    if setup:
        cli.main(["setup", "--no-link"])
        cli.main(["mute"])  # a decision is made and logged, nothing is spoken
    r = subprocess.run(
        [*entry(), "hook"], input=raw.encode(), capture_output=True, env=dict(os.environ), timeout=20
    )
    assert (r.returncode, r.stdout, r.stderr) == (0, b"", b"")


def test_entry_point_is_fast() -> None:
    cli.main(["setup", "--no-link"])
    cli.main(["mute"])
    raw = payload("PreToolUse", tool_name="AskUserQuestion").encode()
    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        subprocess.run([*entry(), "hook"], input=raw, capture_output=True, env=dict(os.environ), timeout=20)
        times.append(time.perf_counter() - t0)
    assert statistics.median(times) < 0.100, f"median {statistics.median(times) * 1000:.0f} ms"
