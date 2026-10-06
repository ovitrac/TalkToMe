"""Event → utterance decision (design §3–§5). Pure: no I/O, the clock and the random source are arguments.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import json
import random
import zlib
from dataclasses import asdict, dataclass, replace
from pathlib import PurePath
from typing import Any

from . import catalog, config, gender, moods
from .state import SessionState

# Notification types and tools that block Claude until the user acts.
HELP_TOOLS = frozenset({"AskUserQuestion", "ExitPlanMode"})
NOTIFICATIONS = {"permission_prompt": "attention", "idle_prompt": "input", "elicitation_dialog": "help"}
FALLBACK_SESSION = {"en": "this session", "fr": "cette session"}
FR_PITCH_OFFSETS = (-2.0, -1.0, 0.0, 1.0, 2.0)
PITCH_LIMIT = 4.0


@dataclass(frozen=True)
class Event:
    kind: str  # "prompt" | "pretool" | "notification" | "stop" | "say" | "test"
    session_id: str = ""
    cwd: str = ""
    session_name: str = ""  # TALKTOME_SESSION given at launch
    tool_name: str = ""
    notification_type: str = ""
    stop_hook_active: bool = False
    text: str = ""
    mood: str = ""
    cls: str = ""


@dataclass(frozen=True)
class Utterance:
    session_id: str
    session: str
    event: str
    cls: str
    register: str
    lang: str
    text: str
    mood: str
    voice: str
    speed: float
    pitch_st: float
    earcon: bool
    gender: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, s: str) -> Utterance:
        return cls(**json.loads(s))


@dataclass(frozen=True)
class Decision:
    utterance: Utterance | None
    reason: str
    state: SessionState


def classify(event: Event) -> str | None:
    if event.kind == "pretool":
        return "help" if event.tool_name in HELP_TOOLS else None
    if event.kind == "notification":
        return NOTIFICATIONS.get(event.notification_type)
    if event.kind == "stop":
        return "landed"
    if event.kind in ("say", "test"):
        return event.cls or "say"
    return None


def session_name(event: Event, st: SessionState, lang: str) -> str:
    """Name given from inside the session, else at launch, else the working-directory basename."""
    for candidate in (st.name, event.session_name, PurePath(event.cwd).name if event.cwd else ""):
        if candidate and candidate.strip():
            return candidate.strip()
    return FALLBACK_SESSION[lang]


def session_gender(st: SessionState, cfg: dict[str, Any], session: str) -> str:
    """Gender set for the session, else the user's map, else improvised from the name."""
    if st.gender in config.GENDERS:
        return st.gender
    mapped = cfg["genders"].get(session)
    return mapped if mapped in config.GENDERS else gender.guess(session)[0]


def _voice_and_pitch(
    cfg: dict[str, Any], lang: str, session: str, sex: str, mood_pitch: float
) -> tuple[str, float]:
    voice = config.voice_for(cfg, lang, sex)
    if cfg["register"] != "fun":
        return voice, 0.0
    pitch = mood_pitch
    if cfg["fun"]["voice_per_session"]:
        h = zlib.crc32(session.encode("utf-8"))
        if (
            lang == "en"
        ):  # a voice of the session's gender: the second letter of a Kokoro name (bf_, bm_, af_, am_)
            pool = [v for v in cfg["fun"]["voice_pool"] if v[1] == sex] or [voice]
            voice = pool[h % len(pool)]
        else:  # one French voice: sessions differ by pitch
            pitch += FR_PITCH_OFFSETS[h % len(FR_PITCH_OFFSETS)]
    return voice, max(-PITCH_LIMIT, min(PITCH_LIMIT, pitch))


def build(
    event: Event, st: SessionState, cfg: dict[str, Any], cls: str, rng: random.Random
) -> tuple[Utterance, SessionState]:
    """Compose the utterance for class `cls`; returns it with the rotation state to keep."""
    lang, register = cfg["language"], cfg["register"]
    session = session_name(event, st, lang)
    sex = session_gender(st, cfg, session)
    mood = moods.get(event.mood or cfg["moods"].get(cls, "neutral"))
    variants = st.variants
    if event.kind == "say":
        text = catalog.substitute(event.text, cfg["name"], session, sex)
    else:
        pool = catalog.templates(cfg, register, lang, cls)
        idx = 0
        if register == "fun" and len(pool) > 1:
            last = st.variants.get(cls)
            idx = rng.choice([i for i in range(len(pool)) if i != last])
        variants = {**st.variants, cls: idx}
        text = catalog.substitute(pool[idx], cfg["name"], session, sex)
    voice, pitch = _voice_and_pitch(cfg, lang, session, sex, mood.pitch_st)
    utt = Utterance(
        session_id=event.session_id,
        session=session,
        event=event.kind,
        cls=cls,
        register=register,
        lang=lang,
        text=text,
        mood=mood.name,
        voice=voice,
        speed=round(config.speed_for(cfg, lang) * mood.speed, 4),
        pitch_st=pitch,
        earcon=bool(cfg["earcons"]),
        gender=sex,
    )
    return utt, replace(st, variants=variants)


def decide(event: Event, st: SessionState, cfg: dict[str, Any], now: float, rng: random.Random) -> Decision:
    if event.kind == "prompt":
        return Decision(None, "turn start", replace(st, turn_start=now))
    cls = classify(event)
    if cls is None:
        return Decision(None, "not an alert", st)
    if event.kind == "test":  # explicit request: no threshold, no mute, no alert bookkeeping
        utt, st = build(event, st, cfg, cls, rng)
        return Decision(utt, "test", st)
    th = cfg["thresholds"]
    if event.kind == "stop":
        after = replace(st, turn_start=None)
        if event.stop_hook_active:
            return Decision(None, "stop hook active", after)
        if st.turn_start is None:
            return Decision(None, "no turn start", after)
        if now - st.turn_start < th["landed_min_turn_s"]:
            return Decision(None, "short turn", after)
        if st.last_say is not None and st.last_say >= st.turn_start:
            return Decision(None, "said during the turn", after)
        st = after
    alert = event.kind != "say"
    if cls == "input" and st.last_spoken is not None and now - st.last_spoken < th["input_cooldown_s"]:
        return Decision(None, "cooldown", st)
    if alert and st.last_alert is not None and now - st.last_alert < th["debounce_s"]:
        return Decision(None, "debounce", st)
    if config.is_muted(cfg, now):
        return Decision(None, "muted", st)
    utt, st = build(event, st, cfg, cls, rng)
    st = replace(
        st,
        last_spoken=now,
        last_alert=now if alert else st.last_alert,
        last_say=now if event.kind == "say" else st.last_say,
    )
    return Decision(utt, "spoken", st)
