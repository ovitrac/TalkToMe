"""T1 — decide() follows the event mapping and noise rules (design §3) and the registers (design §5).

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from talktome import catalog, moods
from talktome.decide import Event, Utterance, decide, session_name
from talktome.state import SessionState

SID = "s-1"
CWD = "/work/alpha"


def ev(kind: str, **kw: Any) -> Event:
    return Event(kind=kind, session_id=SID, cwd=CWD, **kw)


def run(e: Event, st: SessionState, cfg: dict[str, Any], now: float, seed: int = 0) -> Any:
    return decide(e, st, cfg, now, random.Random(seed))


# --- mapping ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "event, cls",
    [
        (ev("pretool", tool_name="AskUserQuestion"), "help"),
        (ev("pretool", tool_name="ExitPlanMode"), "help"),
        (ev("pretool", tool_name="Bash"), None),
        (ev("notification", notification_type="permission_prompt"), "attention"),
        (ev("notification", notification_type="idle_prompt"), "input"),
        (ev("notification", notification_type="elicitation_dialog"), "help"),
        (ev("notification", notification_type="auth_success"), None),
    ],
)
def test_mapping(event: Event, cls: str | None, cfg: dict[str, Any]) -> None:
    d = run(event, SessionState(), cfg, 1000.0)
    assert (d.utterance.cls if d.utterance else None) == cls


def test_prompt_records_turn_start(cfg: dict[str, Any]) -> None:
    d = run(ev("prompt"), SessionState(), cfg, 1000.0)
    assert d.utterance is None and d.state.turn_start == 1000.0


# --- landed and the 60 s threshold -----------------------------------------------------------------


@pytest.mark.parametrize("elapsed, spoken", [(59.9, False), (60.0, True), (3600.0, True)])
def test_landed_threshold(elapsed: float, spoken: bool, cfg: dict[str, Any]) -> None:
    d = run(ev("stop"), SessionState(turn_start=1000.0), cfg, 1000.0 + elapsed)
    assert (d.utterance is not None) == spoken
    assert d.state.turn_start is None


def test_landed_needs_a_turn_start(cfg: dict[str, Any]) -> None:
    assert run(ev("stop"), SessionState(), cfg, 5000.0).reason == "no turn start"


def test_landed_not_when_stop_hook_active(cfg: dict[str, Any]) -> None:
    d = run(ev("stop", stop_hook_active=True), SessionState(turn_start=0.0), cfg, 5000.0)
    assert d.utterance is None and d.reason == "stop hook active"


def test_second_stop_is_silent(cfg: dict[str, Any]) -> None:
    d1 = run(ev("stop"), SessionState(turn_start=0.0), cfg, 100.0)
    d2 = run(ev("stop"), d1.state, cfg, 200.0)
    assert d1.utterance is not None and d2.utterance is None


def test_say_replaces_landed_of_the_same_turn(cfg: dict[str, Any]) -> None:
    st = run(ev("prompt"), SessionState(), cfg, 0.0).state
    st = run(ev("say", text="Tests are red on {session}."), st, cfg, 50.0).state
    assert run(ev("stop"), st, cfg, 100.0).reason == "said during the turn"


def test_say_before_the_turn_does_not_suppress(cfg: dict[str, Any]) -> None:
    st = run(ev("say", text="Hello."), SessionState(), cfg, 0.0).state
    st = run(ev("prompt"), st, cfg, 10.0).state
    assert run(ev("stop"), st, cfg, 100.0).utterance is not None


# --- debounce, cooldown, mute ------------------------------------------------------------------------


def test_debounce(cfg: dict[str, Any]) -> None:
    ask = ev("pretool", tool_name="AskUserQuestion")
    perm = ev("notification", notification_type="permission_prompt")
    st = run(ask, SessionState(), cfg, 1000.0).state
    assert run(perm, st, cfg, 1010.0).reason == "debounce"
    assert run(perm, st, cfg, 1016.0).utterance is not None


def test_input_is_a_reminder(cfg: dict[str, Any]) -> None:
    idle = ev("notification", notification_type="idle_prompt")
    st = run(ev("stop"), SessionState(turn_start=0.0), cfg, 100.0).state
    assert run(idle, st, cfg, 160.0).reason == "cooldown"
    assert run(idle, st, cfg, 401.0).utterance is not None


def test_say_ignores_debounce(cfg: dict[str, Any]) -> None:
    st = run(ev("pretool", tool_name="AskUserQuestion"), SessionState(), cfg, 1000.0).state
    assert run(ev("say", text="Now."), st, cfg, 1001.0).utterance is not None


@pytest.mark.parametrize("patch", [{"mute": True}, {"mute_until": 2000.0}])
def test_muted(patch: dict[str, Any], cfg: dict[str, Any]) -> None:
    d = run(ev("pretool", tool_name="AskUserQuestion"), SessionState(), {**cfg, **patch}, 1000.0)
    assert d.utterance is None and d.reason == "muted" and d.state.last_alert is None


def test_mute_expired(cfg: dict[str, Any]) -> None:
    d = run(ev("pretool", tool_name="AskUserQuestion"), SessionState(), {**cfg, "mute_until": 500.0}, 1000.0)
    assert d.utterance is not None


def test_test_event_bypasses_mute_and_bookkeeping(cfg: dict[str, Any]) -> None:
    d = run(ev("test", cls="landed"), SessionState(), {**cfg, "mute": True}, 1000.0)
    assert d.utterance is not None and d.state.last_alert is None and d.state.last_spoken is None


# --- text, session name, registers ------------------------------------------------------------------


def test_useful_text(cfg: dict[str, Any]) -> None:
    u: Utterance = run(ev("stop"), SessionState(turn_start=0.0), cfg, 100.0).utterance
    assert u.text == "Ada, the results of alpha landed."
    # "alpha" ends in -a: improvised as feminine, so the female English voice speaks.
    assert (u.register, u.lang, u.mood, u.voice, u.pitch_st, u.gender) == (
        "useful",
        "en",
        "cheerful",
        "bf_emma",
        0.0,
        "f",
    )
    assert u.speed == pytest.approx(moods.MOODS["cheerful"].speed)


def test_speed_per_language(cfg: dict[str, Any]) -> None:
    c = {**cfg, "speed": {"en": 1.2, "fr": 1.0}}
    u_en = run(ev("stop"), SessionState(turn_start=0.0), c, 100.0).utterance
    u_fr = run(ev("stop"), SessionState(turn_start=0.0), {**c, "language": "fr"}, 100.0).utterance
    assert u_en.speed == pytest.approx(1.2 * moods.MOODS["cheerful"].speed)
    assert u_fr.speed == pytest.approx(1.0 * moods.MOODS["cheerful"].speed)


def test_useful_text_french_without_name(cfg: dict[str, Any]) -> None:
    c = {**cfg, "language": "fr", "name": ""}
    u = run(ev("stop"), SessionState(turn_start=0.0), c, 100.0).utterance
    assert u.text == "Les résultats d'alpha sont déposés."  # elision and u.voice == "ff_siwis"


def test_session_name_precedence() -> None:
    e = Event(kind="stop", cwd="/work/alpha", session_name="Launch name")
    assert session_name(e, SessionState(name="Given name"), "en") == "Given name"
    assert session_name(e, SessionState(), "en") == "Launch name"
    assert session_name(Event(kind="stop", cwd="/work/alpha"), SessionState(), "en") == "alpha"
    assert session_name(Event(kind="stop"), SessionState(), "fr") == "cette session"


def test_say_text_and_mood(cfg: dict[str, Any]) -> None:
    u = run(
        ev("say", text="Hi {name}, tests are red on {session}.", mood="sorry"), SessionState(), cfg, 0.0
    ).utterance
    assert u.text == "Hi Ada, tests are red on alpha." and u.mood == "sorry" and u.cls == "say"
    assert u.pitch_st == 0.0  # useful register: speed and earcon only


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("cls_event", ["help", "landed"])
def test_fun_rotation_never_repeats(lang: str, cls_event: str, cfg: dict[str, Any]) -> None:
    c = {**cfg, "register": "fun", "language": lang}
    e = ev("pretool", tool_name="AskUserQuestion") if cls_event == "help" else ev("stop")
    st, texts, now = SessionState(), [], 0.0
    for i in range(60):
        now += 1000.0
        if cls_event == "landed":
            st = run(ev("prompt"), st, c, now - 100.0).state
        d = run(e, st, c, now, seed=i)
        assert d.utterance is not None
        texts.append(d.utterance.text)
        st = d.state
    assert all(a != b for a, b in zip(texts, texts[1:]))
    assert len(set(texts)) == len(catalog.builtin()["fun"][lang][cls_event])


def test_fun_voice_per_session(cfg: dict[str, Any]) -> None:
    c = {**cfg, "register": "fun"}
    voices = set()
    for name in ("alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"):
        e = Event(kind="pretool", tool_name="AskUserQuestion", session_id=name, cwd=f"/w/{name}")
        u1 = run(e, SessionState(), c, 0.0, seed=1).utterance
        u2 = run(e, SessionState(), c, 0.0, seed=2).utterance
        assert u1.voice == u2.voice and u1.voice in c["fun"]["voice_pool"]
        assert u1.pitch_st == moods.MOODS["warm"].pitch_st
        voices.add(u1.voice)
    assert len(voices) > 1


def test_fun_french_pitch_per_session(cfg: dict[str, Any]) -> None:
    c = {**cfg, "register": "fun", "language": "fr"}
    pitches = set()
    for name in ("alpha", "beta", "gamma", "delta", "epsilon", "zeta"):
        e = Event(kind="stop", session_id=name, cwd=f"/w/{name}")
        u = run(e, SessionState(turn_start=0.0), c, 100.0).utterance
        assert u.voice == "ff_siwis" and -4.0 <= u.pitch_st <= 4.0
        pitches.add(u.pitch_st)
    assert len(pitches) > 1


def test_utterance_json_roundtrip(cfg: dict[str, Any]) -> None:
    u = run(ev("stop"), SessionState(turn_start=0.0), cfg, 100.0).utterance
    assert Utterance.from_json(u.to_json()) == u
