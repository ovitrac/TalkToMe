"""Configuration: defaults, validation, set/show, mute.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from talktome import config, paths


def test_defaults_are_valid() -> None:
    assert config.validate(config.defaults()) == []


def test_load_without_file_returns_defaults() -> None:
    assert not config.exists()
    assert config.load() == config.defaults()


def test_save_load_roundtrip(cfg: dict[str, Any]) -> None:
    p = config.save(cfg)
    assert p == paths.config_file()
    assert config.load() == cfg


def test_partial_user_file_is_merged() -> None:
    paths.config_file().parent.mkdir(parents=True)
    paths.config_file().write_text(json.dumps({"schema": config.SCHEMA, "language": "fr"}))
    c = config.load()
    assert c["language"] == "fr" and c["voices"] == config.DEFAULTS["voices"]


@pytest.mark.parametrize(
    "content",
    ["{not json", "[]", json.dumps({"schema": config.SCHEMA, "language": "de"}), json.dumps({"bogus": 1})],
)
def test_invalid_file_is_refused(content: str) -> None:
    paths.config_file().parent.mkdir(parents=True)
    paths.config_file().write_text(content)
    with pytest.raises(config.ConfigError):
        config.load()


@pytest.mark.parametrize(
    "key, raw, expected",
    [
        ("name", "Olivier", "Olivier"),
        ("name", "123", "123"),
        ("language", "fr", "fr"),
        ("register", "fun", "fun"),
        ("speed", "1.1", 1.1),
        ("voices.en", "bf_emma", "bf_emma"),
        ("voices.en", "bm_george:0.7+bm_fable:0.3", "bm_george:0.7+bm_fable:0.3"),
        ("thresholds.landed_min_turn_s", "90", 90),
        ("moods.landed", "warm", "warm"),
        ("respell", '{"ETL2": "E T L 2"}', {"ETL2": "E T L 2"}),
        ("templates.useful.en.help", "{session} wants you.", "{session} wants you."),
    ],
)
def test_set_value(cfg: dict[str, Any], key: str, raw: str, expected: Any) -> None:
    out = config.set_value(cfg, key, raw)
    node: Any = out
    for k in key.split("."):
        node = node[k]
    assert node == expected
    assert cfg != out or raw == ""  # input untouched


@pytest.mark.parametrize(
    "key, raw",
    [
        ("schema", "x"),
        ("unknown", "1"),
        ("voices.de", "x"),
        ("language", "de"),
        ("speed", "3"),
        ("voices.en", "George"),
        ("moods.landed", "ecstatic"),
        ("fun.voice_pool", '["ff_siwis"]'),
        ("templates.useful.en.help", "no session here"),
        ("templates.useful.en.help", "{session} and {who}"),
        ("player", "relative/path"),
    ],
)
def test_set_value_refuses(cfg: dict[str, Any], key: str, raw: str) -> None:
    with pytest.raises(config.ConfigError):
        config.set_value(cfg, key, raw)


def test_speed_per_language(cfg: dict[str, Any]) -> None:
    cfg["speed"] = 1.1  # one number for all languages, as older files have it
    out = config.set_value(cfg, "speed.en", "1.2")
    assert out["speed"] == {**{c: 1.1 for c in cfg["languages"]}, "en": 1.2}
    assert (config.speed_for(out, "en"), config.speed_for(out, "fr")) == (1.2, 1.1)
    assert config.speed_for(cfg, "fr") == 1.1
    with pytest.raises(config.ConfigError):
        config.set_value(out, "speed.en", "2.5")
    assert config.set_value(out, "speed", '{"en": 1.2}')["speed"] == {"en": 1.2}  # others: 1.0
    assert config.speed_for(config.set_value(out, "speed", '{"en": 1.2}'), "es") == 1.0
    with pytest.raises(config.ConfigError):
        config.set_value(out, "speed", '{"xx": 1.2}')


def test_parse_voice() -> None:
    assert config.parse_voice("bm_george") == [("bm_george", 1.0)]
    assert config.parse_voice("bm_george:0.7+bm_fable:0.3") == [("bm_george", 0.7), ("bm_fable", 0.3)]
    with pytest.raises(ValueError):
        config.parse_voice("bm_george:0")


def test_is_muted(cfg: dict[str, Any]) -> None:
    assert not config.is_muted(cfg, 100.0)
    assert config.is_muted({**cfg, "mute": True}, 100.0)
    assert config.is_muted({**cfg, "mute_until": 200.0}, 100.0)
    assert not config.is_muted({**cfg, "mute_until": 50.0}, 100.0)
