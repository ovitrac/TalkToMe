"""Hook fast path (design §2): stdin JSON → session state → decide → detached worker. Stdlib only.

Prints nothing and never raises: on PreToolUse, exit 2 or JSON on stdout would change Claude's behaviour,
and on UserPromptSubmit, stdout would be added to the prompt.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import json
import random
import time
from collections.abc import Mapping
from typing import Any

from . import config, journal, state, worker
from .decide import Event, decide

EVENTS = {
    "UserPromptSubmit": "prompt",
    "PreToolUse": "pretool",
    "Notification": "notification",
    "Stop": "stop",
}


def _str(payload: Mapping[str, Any], key: str) -> str:
    v = payload.get(key)
    return v if isinstance(v, str) else ""


def notification_type(payload: Mapping[str, Any]) -> str:
    """`notification_type` when present; otherwise inferred from the message (older Claude Code versions)."""
    t = _str(payload, "notification_type")
    if t:
        return t
    msg = _str(payload, "message").lower()
    if "permission" in msg:
        return "permission_prompt"
    if "waiting for your input" in msg:
        return "idle_prompt"
    return ""


def event_from_payload(payload: Mapping[str, Any], env: Mapping[str, str]) -> Event | None:
    kind = EVENTS.get(_str(payload, "hook_event_name"))
    if kind is None:
        return None
    return Event(
        kind=kind,
        session_id=_str(payload, "session_id"),
        cwd=_str(payload, "cwd"),
        session_name=env.get("TALKTOME_SESSION", ""),
        session_mode=env.get("TALKTOME", ""),
        tool_name=_str(payload, "tool_name"),
        notification_type=notification_type(payload) if kind == "notification" else "",
        stop_hook_active=payload.get("stop_hook_active") is True,
    )


def run(raw: str, env: Mapping[str, str], now: float | None = None) -> str:
    """Handle one hook invocation and return the decision reason (for tests and logs). Never raises."""
    try:
        payload = json.loads(raw) if raw.strip() else None
        if not isinstance(payload, dict):
            return "no input"
        ev = event_from_payload(payload, env)
        if ev is None:
            return "ignored event"
        if not config.exists():
            return "not configured"
        cfg = config.load()
        t = time.time() if now is None else now
        with state.locked(ev.session_id):
            d = decide(ev, state.load(ev.session_id), cfg, t, random.Random())
            state.save(ev.session_id, d.state)
        if d.utterance is not None:
            worker.spawn(d.utterance)
        elif ev.kind != "prompt" and d.reason != "not an alert":
            journal.append(
                {"session_id": ev.session_id, "event": ev.kind, "outcome": f"suppressed: {d.reason}"}
            )
        return d.reason
    except Exception as e:
        try:
            journal.append({"outcome": f"error: hook: {type(e).__name__}: {e}"})
        except Exception:
            pass
        return "error"
