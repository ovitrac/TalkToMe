"""`talktome` command line (design §7). Light imports at module level; heavy ones inside the commands.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from . import __version__, config, paths, state
from .decide import Event, Utterance, decide
from .moods import MOODS

MAX_SAY_CHARS = 280
REDACTION_TAG = re.compile(r"\bTAG-[0-9A-Za-z]{4,}\b")


def _err(msg: str) -> int:
    print(f"talktome: {msg}", file=sys.stderr)
    return 2


def _load(required: bool = True) -> dict[str, Any] | None:
    if required and not config.exists():
        _err("not configured yet — run `talktome setup`")
        return None
    try:
        return config.load()
    except config.ConfigError as e:
        _err(str(e))
        return None


def _session_event(kind: str, **kw: Any) -> Event:
    return Event(
        kind=kind,
        session_id=os.environ.get("CLAUDE_CODE_SESSION_ID", "") or "cli",
        cwd=os.getcwd(),
        session_name=os.environ.get("TALKTOME_SESSION", ""),
        **kw,
    )


def _report(rec: dict[str, Any]) -> int:
    print(
        f"{rec.get('outcome')} · {rec.get('engine', '-')} · cache {rec.get('cache', '-')} · "
        f"synth {rec.get('synth_s', '-')} s · play {rec.get('play_s', '-')} s · "
        f"total {rec.get('total_s', '-')} s"
    )
    print(
        f"  “{rec.get('text')}” — {rec.get('voice')}, {rec.get('mood')}, speed {rec.get('speed')}, "
        f"pitch {rec.get('pitch_st')} st"
    )
    return 0 if rec.get("outcome") in ("played", "spoken") else 1


# --- commands -------------------------------------------------------------------------------------------


def cmd_hook(a: argparse.Namespace) -> int:
    """Claude Code hook entry: reads the event on stdin, prints nothing, always exits 0."""
    from . import hook

    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return 0
    hook.run(raw, os.environ)
    return 0


def cmd_say(a: argparse.Namespace) -> int:
    text = " ".join(a.text).strip()
    if not text:
        return _err("nothing to say")
    if len(text) > MAX_SAY_CHARS:
        return _err(f"refused: {len(text)} characters (max {MAX_SAY_CHARS}); keep it to one or two sentences")
    if REDACTION_TAG.search(text):
        return _err("refused: the text contains a redaction placeholder")
    cfg = _load()
    if cfg is None:
        return 2
    from . import journal, worker

    ev = _session_event("say", text=text, mood=a.mood or "", cls=a.cls or "")
    with state.locked(ev.session_id):
        d = decide(ev, state.load(ev.session_id), cfg, time.time(), random.Random())
        state.save(ev.session_id, d.state)
    if d.utterance is None:
        journal.append({"session_id": ev.session_id, "event": "say", "outcome": f"suppressed: {d.reason}"})
        print(f"talktome: not spoken ({d.reason})", file=sys.stderr)
        return 0
    if a.wait:
        return _report(worker.speak(d.utterance, cfg))
    worker.spawn(d.utterance)
    return 0


def _describe(sid: str) -> str:
    """“name” — she/he (how the gender was decided), for the current session."""
    from . import gender
    from .decide import session_gender, session_name

    cfg = _load(required=False) or config.defaults()
    st = state.load(sid)
    ev = _session_event("test")
    name = session_name(ev, st, cfg["language"])
    sex = session_gender(st, cfg, name)
    how = "set" if st.gender else "your map" if name in cfg["genders"] else gender.guess(name)[1]
    return f"“{name}” — {'she' if sex == 'f' else 'he'} ({how})"


def cmd_name(a: argparse.Namespace) -> int:
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if not sid:
        return _err("no Claude Code session here; set TALKTOME_SESSION when launching instead")
    name = " ".join(a.name).strip()
    with state.locked(sid):
        state.save(sid, replace(state.load(sid), name=name or None, gender=a.gender))
    print(f"this session is now {_describe(sid)}" if name else f"session name cleared: {_describe(sid)}")
    return 0


def cmd_gender(a: argparse.Namespace) -> int:
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if not sid:
        return _err("no Claude Code session here; use `talktome set genders.NAME f|m` instead")
    if a.gender:
        with state.locked(sid):
            st = state.load(sid)
            state.save(sid, replace(st, gender=None if a.gender == "auto" else a.gender))
    print(f"this session is {_describe(sid)}")
    return 0


def cmd_set(a: argparse.Namespace) -> int:
    cfg = _load(required=False)
    if cfg is None:
        return 2
    try:
        cfg = config.set_value(cfg, a.key, a.value)
        config.save(cfg)
    except config.ConfigError as e:
        return _err(str(e))
    node: Any = cfg
    for k in a.key.split("."):
        node = node[k]
    print(f"{a.key} = {json.dumps(node, ensure_ascii=False)}")
    return 0


def cmd_show(a: argparse.Namespace) -> int:
    cfg = _load(required=False)
    if cfg is None:
        return 2
    print(
        f"# {paths.config_file()}{'' if config.exists() else ' (not created yet: defaults)'}", file=sys.stderr
    )
    print(json.dumps(cfg, indent=1, ensure_ascii=False))
    return 0


def cmd_voices(a: argparse.Namespace) -> int:
    cfg = _load(required=False)
    if cfg is None:
        return 2
    from . import engine, models

    d = models.resolve_dir(cfg)
    if d is None:
        return _err("no model directory configured (talktome setup)")
    prefixes = {"en": ("a", "b"), "fr": ("f",)}.get(a.lang or "", None)
    for v in engine.Kokoro(d).voices():
        if prefixes is None or v.startswith(prefixes):
            print(v)
    return 0


def cmd_mute(a: argparse.Namespace) -> int:
    cfg = _load(required=False)
    if cfg is None:
        return 2
    if a.minutes:
        cfg["mute_until"] = time.time() + 60.0 * a.minutes
        msg = (
            f"muted for {a.minutes:g} min (until {time.strftime('%H:%M', time.localtime(cfg['mute_until']))})"
        )
    else:
        cfg["mute"] = True
        msg = "muted until `talktome unmute`"
    config.save(cfg)
    print(msg)
    return 0


def cmd_unmute(a: argparse.Namespace) -> int:
    cfg = _load(required=False)
    if cfg is None:
        return 2
    cfg["mute"], cfg["mute_until"] = False, None
    config.save(cfg)
    print("unmuted")
    return 0


def cmd_test(a: argparse.Namespace) -> int:
    cfg = _load()
    if cfg is None:
        return 2
    for key, value in (("register", a.register), ("language", a.language)):
        if value:
            cfg[key] = value
    from . import worker

    ev = _session_event("test", cls=a.cls, mood=a.mood or "")
    d = decide(ev, state.load(ev.session_id), cfg, time.time(), random.Random())
    assert isinstance(d.utterance, Utterance)
    return _report(worker.speak(d.utterance, cfg))


def cmd_doctor(a: argparse.Namespace) -> int:
    from . import journal, models, player

    failures = 0

    def line(ok: bool, label: str, detail: str) -> None:
        nonlocal failures
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {label:10} {detail}")

    cfg: dict[str, Any] | None = None
    if not config.exists():
        line(False, "config", f"{paths.config_file()} missing — run `talktome setup`")
    else:
        try:
            cfg = config.load()
            muted = ", MUTED" if config.is_muted(cfg, time.time()) else ""
            voice = "/".join(config.voice_for(cfg, cfg["language"], g) for g in config.GENDERS)
            line(
                True,
                "config",
                f"{paths.config_file()} ({cfg['language']}, {cfg['register']}, {voice}{muted})",
            )
        except config.ConfigError as e:
            line(False, "config", str(e))
    c = cfg or config.defaults()
    d = models.resolve_dir(c)
    if d is None:
        line(False, "models", "no model directory (talktome setup --models-dir DIR | --fetch)")
    else:
        t0 = time.monotonic()
        errors = models.verify(d)
        line(
            not errors,
            "models",
            "; ".join(errors) or f"{d} — SHA-256 verified in {time.monotonic() - t0:.1f} s",
        )
    try:
        import kokoro_onnx  # noqa: F401

        line(True, "engine", "kokoro-onnx importable")
    except ImportError as e:
        line(False, "engine", f"kokoro-onnx not importable: {e}")
    argv = player.find(c["player"])
    line(argv is not None, "player", argv[0] if argv else f"none found for {c['player']!r}")
    line(
        shutil.which("spd-say") is not None,
        "fallback",
        shutil.which("spd-say") or "spd-say not found (optional)",
    )
    target = Path(sys.executable).parent / "talktome"
    found = shutil.which("talktome")
    on_path = found is not None and Path(found).resolve() == target.resolve()
    line(
        on_path,
        "PATH",
        f"{found} → {target}" if on_path else f"`talktome` on PATH is {found!r}, expected {target}",
    )
    try:
        paths.state_dir().mkdir(parents=True, exist_ok=True)
        line(os.access(paths.state_dir(), os.W_OK), "state", str(paths.state_dir()))
    except OSError as e:
        line(False, "state", str(e))
    for rec in journal.tail(3):
        print(
            f"      log  {rec.get('ts', '?')[:19]}  {rec.get('session', rec.get('session_id', '?'))}: "
            f"{rec.get('outcome')}  “{rec.get('text', '')}”"
        )
    return 1 if failures else 0


def cmd_setup(a: argparse.Namespace) -> int:
    from . import models

    try:
        cfg = config.load() if config.exists() else config.defaults()
    except config.ConfigError as e:
        return _err(f"{e} — fix or remove the file first")
    if a.name is not None:
        cfg["name"] = a.name
    if a.language:
        cfg["language"] = a.language
    if a.models_dir:
        d = Path(a.models_dir).expanduser().resolve()
        print(f"verifying {d} …")
        errors = models.verify(d)
        if errors:
            return _err("; ".join(errors))
        cfg["models_dir"] = str(d)
    elif a.fetch:
        d = models.default_dir()
        print(f"downloading the Kokoro model files (338 MB) into {d} …")
        try:
            models.fetch(d)
        except (OSError, models.ModelError) as e:
            return _err(str(e))
        cfg["models_dir"] = str(d)
    try:
        print(f"config: {config.save(cfg)}")
    except config.ConfigError as e:
        return _err(str(e))
    if not cfg["models_dir"] and models.resolve_dir(cfg) is None:
        print("models: none yet — run `talktome setup --models-dir DIR` or `talktome setup --fetch`")
    if not a.no_link:
        target = Path(sys.executable).parent / "talktome"
        link = Path.home() / ".local" / "bin" / "talktome"
        if link.exists() and not link.is_symlink():
            print(f"link: {link} exists and is not a symlink; left untouched")
        elif link.is_symlink() and link.resolve() == target.resolve():
            print(f"link: {link} → {target} (already)")
        else:
            link.parent.mkdir(parents=True, exist_ok=True)
            if link.is_symlink():
                link.unlink()
            link.symlink_to(target)
            print(f"link: {link} → {target}")
    return 0


# --- parser ---------------------------------------------------------------------------------------------


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="talktome", description="Spoken alerts from concurrent Claude Code sessions."
    )
    p.add_argument("--version", action="version", version=f"talktome {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    s = sub.add_parser("hook", help="Claude Code hook entry (event JSON on stdin; silent)")
    s.set_defaults(func=cmd_hook)

    s = sub.add_parser("say", help="speak a message (from the skill or by hand)")
    s.add_argument("text", nargs="+")
    s.add_argument("--mood", choices=sorted(MOODS))
    s.add_argument("--class", dest="cls", choices=config.CLASSES)
    s.add_argument("--wait", action="store_true", help="speak now and report, instead of detaching")
    s.set_defaults(func=cmd_say)

    s = sub.add_parser("name", help="give the current Claude Code session a spoken name")
    s.add_argument("name", nargs="*")
    s.add_argument("--gender", choices=config.GENDERS, help="f or m; omitted: improvised from the name")
    s.set_defaults(func=cmd_name)

    s = sub.add_parser(
        "gender", help="show, set (f, m) or improvise again (auto) the current session's gender"
    )
    s.add_argument("gender", nargs="?", choices=(*config.GENDERS, "auto"))
    s.set_defaults(func=cmd_gender)

    s = sub.add_parser(
        "set", help="set a configuration value, e.g. `set language fr`, `set voices.en bf_emma`"
    )
    s.add_argument("key")
    s.add_argument("value")
    s.set_defaults(func=cmd_set)

    sub.add_parser("show", help="print the effective configuration").set_defaults(func=cmd_show)

    s = sub.add_parser("voices", help="list the available voices")
    s.add_argument("--lang", choices=config.LANGUAGES)
    s.set_defaults(func=cmd_voices)

    s = sub.add_parser("mute", help="silence TalkToMe (indefinitely, or for MINUTES)")
    s.add_argument("minutes", nargs="?", type=float)
    s.set_defaults(func=cmd_mute)

    sub.add_parser("unmute", help="end a mute").set_defaults(func=cmd_unmute)

    s = sub.add_parser("test", help="speak a sample alert now")
    s.add_argument("--class", dest="cls", choices=config.CLASSES, default="landed")
    s.add_argument("--mood", choices=sorted(MOODS))
    s.add_argument("--register", choices=config.REGISTERS)
    s.add_argument("--language", choices=config.LANGUAGES)
    s.set_defaults(func=cmd_test)

    sub.add_parser("doctor", help="check configuration, models, player and PATH").set_defaults(
        func=cmd_doctor
    )

    s = sub.add_parser("setup", help="create the configuration, locate or fetch the models, link the command")
    s.add_argument("--name", help="how TalkToMe addresses you (empty: no name)")
    s.add_argument("--language", choices=config.LANGUAGES)
    g = s.add_mutually_exclusive_group()
    g.add_argument("--models-dir", help="directory holding kokoro-v1.0.onnx and voices-v1.0.bin")
    g.add_argument("--fetch", action="store_true", help="download the model files (network)")
    s.add_argument("--no-link", action="store_true", help="do not create ~/.local/bin/talktome")
    s.set_defaults(func=cmd_setup)
    return p


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    func: Callable[[argparse.Namespace], int] = a.func
    return func(a)


if __name__ == "__main__":
    sys.exit(main())
