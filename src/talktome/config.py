"""User configuration (design §6): one JSON file, one schema version, validated. Standard library only.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from . import langs, paths
from .moods import MOODS

SCHEMA = "talktome-config/1"
REGISTERS = ("useful", "fun")
CLASSES = ("help", "attention", "input", "landed")
PLAYERS = ("auto", "pw-play", "paplay", "aplay", "afplay", "ffplay", "mpv")
FREE_KEYS = ("templates", "respell", "genders", "private", "voices", "speed")
GENDERS = ("f", "m")
MODES = ("on", "discreet", "off")

DEFAULTS: dict[str, Any] = {
    "schema": SCHEMA,
    "name": "",
    "language": "en",
    "languages": list(langs.DEFAULT_LANGUAGES),
    "register": "useful",
    "voices": {},  # overrides of the packs' voices: {"en": "bm_lewis"} or {"en": {"f": "af_heart", "m": "…"}}
    "speed": 1.0,  # one number for every language, or {"en": 1.2, "fr": 1.0}
    "volume": 1.0,
    "earcons": True,
    "mute": False,
    "mute_until": None,
    "models_dir": "",
    "player": "auto",
    "thresholds": {"landed_min_turn_s": 60, "debounce_s": 15, "input_cooldown_s": 300},
    "moods": {"help": "warm", "attention": "firm", "input": "calm", "landed": "cheerful"},
    "fun": {
        "voice_pool": ["bm_george", "bf_emma", "am_michael", "af_heart", "bm_lewis", "bf_isabella"],
        "voice_per_session": True,
    },
    "templates": {},
    "respell": {},
    "genders": {},
    "private": {},
}

_VOICE = re.compile(r"^[a-z]{2}_[a-z0-9]+$")


class ConfigError(Exception):
    pass


def defaults() -> dict[str, Any]:
    return copy.deepcopy(DEFAULTS)


def _merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict) and k not in FREE_KEYS:
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def exists(path: Path | None = None) -> bool:
    return (path or paths.config_file()).is_file()


def load(path: Path | None = None) -> dict[str, Any]:
    """Defaults overlaid with the user file; raises ConfigError on unreadable or invalid content."""
    p = path or paths.config_file()
    if not p.is_file():
        return defaults()
    try:
        user = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ConfigError(f"{p}: {e}") from e
    if not isinstance(user, dict):
        raise ConfigError(f"{p}: top level must be an object")
    cfg = _merge(DEFAULTS, user)
    errors = validate(cfg)
    if errors:
        raise ConfigError(f"{p}: " + "; ".join(errors))
    return cfg


def save(cfg: dict[str, Any], path: Path | None = None) -> Path:
    errors = validate(cfg)
    if errors:
        raise ConfigError("; ".join(errors))
    p = path or paths.config_file()
    paths.write_json_atomic(p, cfg)
    return p


def parse_voice(spec: str) -> list[tuple[str, float]]:
    """`bm_george` or a blend `bm_george:0.7+bm_fable:0.3` → [(voice, weight), ...]; raises ValueError."""
    parts: list[tuple[str, float]] = []
    for item in spec.split("+"):
        name, _, w = item.strip().partition(":")
        if not _VOICE.match(name):
            raise ValueError(f"invalid voice name {name!r}")
        weight = float(w) if w else 1.0
        if weight <= 0:
            raise ValueError(f"voice weight must be > 0 in {spec!r}")
        parts.append((name, weight))
    return parts


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate(cfg: dict[str, Any]) -> list[str]:
    from . import catalog  # local import: catalog depends on this module's constants

    e: list[str] = []
    unknown = set(cfg) - set(DEFAULTS)
    if unknown:
        e.append(f"unknown keys: {sorted(unknown)}")
    if cfg.get("schema") != SCHEMA:
        e.append(f"schema must be {SCHEMA!r}")
    if not isinstance(cfg.get("name"), str):
        e.append("name must be a string")
    installed = cfg.get("languages")
    if (
        not isinstance(installed, list)
        or not installed
        or len(set(installed)) != len(installed)
        or not set(installed) <= set(langs.codes())
    ):
        e.append(f"languages must be a non-empty list of distinct packs among {langs.codes()}")
        installed = []
    if cfg.get("language") not in installed:
        e.append(f"language must be an installed language ({', '.join(installed)}; `talktome lang add`)")
    if cfg.get("register") not in REGISTERS:
        e.append(f"register must be one of {REGISTERS}")
    voices = cfg.get("voices")
    if not isinstance(voices, dict) or not set(voices) <= set(langs.codes()):
        e.append(f"voices must map languages among {langs.codes()} to a voice, or to one voice per gender")
    else:
        for lang, spec in voices.items():
            specs = spec if isinstance(spec, dict) else {g: spec for g in GENDERS}
            if set(specs) != set(GENDERS):
                e.append(f"voices.{lang}: one voice, or one per gender {GENDERS}")
                continue
            for g, v in specs.items():
                try:
                    parse_voice(v)
                except (ValueError, AttributeError) as x:
                    e.append(f"voices.{lang}.{g}: {x}")
    speed: Any = cfg.get("speed")
    speeds: dict[str, Any] = speed if isinstance(speed, dict) else {"*": speed}
    if not set(speeds) <= {"*", *langs.codes()} or not all(
        _is_num(v) and 0.5 <= v <= 2.0 for v in speeds.values()
    ):
        e.append("speed must be a number in [0.5, 2.0], or one per language")
    if not _is_num(cfg.get("volume")) or not 0.0 <= cfg["volume"] <= 2.0:
        e.append("volume must be a number in [0, 2]")
    for k in ("earcons", "mute"):
        if not isinstance(cfg.get(k), bool):
            e.append(f"{k} must be true or false")
    if cfg.get("mute_until") is not None and not _is_num(cfg.get("mute_until")):
        e.append("mute_until must be null or epoch seconds")
    if not isinstance(cfg.get("models_dir"), str):
        e.append("models_dir must be a string")
    player = cfg.get("player")
    if not isinstance(player, str) or not (player in PLAYERS or player.startswith("/")):
        e.append(f"player must be one of {PLAYERS} or an absolute path")
    th = cfg.get("thresholds")
    if not isinstance(th, dict) or set(th) != set(DEFAULTS["thresholds"]):
        e.append(f"thresholds must have exactly {sorted(DEFAULTS['thresholds'])}")
    else:
        for k, v in th.items():
            if not _is_num(v) or v < 0:
                e.append(f"thresholds.{k} must be a number >= 0")
    moods = cfg.get("moods")
    if not isinstance(moods, dict) or not set(moods) <= set(CLASSES):
        e.append(f"moods keys must be among {CLASSES}")
    else:
        for k, v in moods.items():
            if v not in MOODS:
                e.append(f"moods.{k}: unknown mood {v!r} (known: {sorted(MOODS)})")
    fun = cfg.get("fun")
    if not isinstance(fun, dict) or set(fun) != set(DEFAULTS["fun"]):
        e.append(f"fun must have exactly {sorted(DEFAULTS['fun'])}")
    else:
        pool = fun["voice_pool"]
        if not isinstance(pool, list) or not pool or not all(isinstance(v, str) for v in pool):
            e.append("fun.voice_pool must be a non-empty list of English voices")
        else:
            for v in pool:
                if not _VOICE.match(v) or v[0] not in "ab":
                    e.append(f"fun.voice_pool: {v!r} is not an English voice (a*/b*)")
        if not isinstance(fun["voice_per_session"], bool):
            e.append("fun.voice_per_session must be true or false")
    e.extend(catalog.validate_overrides(cfg.get("templates")))
    genders = cfg.get("genders")
    if not isinstance(genders, dict) or not all(
        isinstance(k, str) and v in GENDERS for k, v in genders.items()
    ):
        e.append(f"genders must map session names to one of {GENDERS}")
    private = cfg.get("private")
    if not isinstance(private, dict) or not all(
        isinstance(k, str) and k and v in MODES for k, v in private.items()
    ):
        e.append(f"private must map folder patterns to one of {MODES}")
    respell = cfg.get("respell")
    if not isinstance(respell, dict) or not all(
        isinstance(k, str) and isinstance(v, str) and k for k, v in respell.items()
    ):
        e.append("respell must map non-empty strings to strings")
    return e


_MISSING = object()


def _get(cfg: dict[str, Any], keys: list[str]) -> Any:
    node: Any = cfg
    for k in keys:
        if not isinstance(node, dict) or k not in node:
            return _MISSING
        node = node[k]
    return node


def set_value(cfg: dict[str, Any], dotted: str, raw: str) -> dict[str, Any]:
    """Return a validated copy of `cfg` with `dotted` set from the command-line string `raw`."""
    keys = dotted.split(".")
    if keys[0] not in DEFAULTS or keys[0] == "schema":
        raise ConfigError(f"unknown or read-only key {dotted!r}")
    if keys[0] not in FREE_KEYS and _get(DEFAULTS, keys) is _MISSING:
        raise ConfigError(f"unknown key {dotted!r}")
    current = _get(DEFAULTS, keys)
    value: Any
    if isinstance(current, str):
        value = raw
    else:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
    out = copy.deepcopy(cfg)
    if keys[0] == "speed" and len(keys) == 2 and not isinstance(out["speed"], dict):
        out["speed"] = {
            lang: out["speed"] for lang in out["languages"]
        }  # one number for all → one per language
    if keys[0] == "voices" and len(keys) == 3 and isinstance(out["voices"].get(keys[1]), str):
        out["voices"][keys[1]] = {g: out["voices"][keys[1]] for g in GENDERS}  # one voice → one per gender
    node = out
    for k in keys[:-1]:
        node = node.setdefault(k, {})
        if not isinstance(node, dict):
            raise ConfigError(f"{dotted!r}: {k!r} is not an object")
    node[keys[-1]] = value
    errors = validate(out)
    if errors:
        raise ConfigError("; ".join(errors))
    return out


def voice_for(cfg: dict[str, Any], lang: str, gender: str) -> str:
    """Voice for `lang` and `gender`: `voices.<lang>` is one voice for both genders or one per gender."""
    spec = cfg["voices"].get(lang)
    if spec is None:
        return langs.voice(lang, gender)
    return str(spec[gender] if isinstance(spec, dict) else spec)


def speed_for(cfg: dict[str, Any], lang: str) -> float:
    """Base speaking rate for `lang`: `speed` is one number for all languages or one per language."""
    speed = cfg["speed"]
    return float(speed.get(lang, 1.0) if isinstance(speed, dict) else speed)


def is_muted(cfg: dict[str, Any], now: float) -> bool:
    until = cfg.get("mute_until")
    return bool(cfg.get("mute")) or (until is not None and now < until)
