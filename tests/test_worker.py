"""T4 serialization, T5 cache, fallback and queue timeout of the speech worker (design §10).

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import fcntl
import json
import multiprocessing as mp
import stat
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile as sf

from talktome import engine, journal, models, paths, player, worker
from talktome.decide import Utterance

U = Utterance(
    session_id="s-1",
    session="alpha",
    event="stop",
    cls="landed",
    register="useful",
    lang="en",
    text="Ada, the results of alpha landed.",
    mood="cheerful",
    voice="bm_george",
    speed=1.05,
    pitch_st=0.0,
    earcon=True,
)


def fake_player(tmp: Path, marks: Path, seconds: float = 0.3) -> str:
    p = tmp / "fakeplay"
    p.write_text(
        f'#!/bin/sh\necho "start $(date +%s.%N)" >> {marks}\nsleep {seconds}\n'
        f'echo "end $(date +%s.%N)" >> {marks}\n'
    )
    p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return str(p)


class StubKokoro:
    calls = 0

    def __init__(self, models_dir: Path) -> None:
        pass

    def synth(self, text: str, voice: str, speed: float, pitch: float) -> np.ndarray:
        StubKokoro.calls += 1
        return (0.5 * np.sin(2 * np.pi * 220 * np.arange(2400) / engine.SR)).astype(np.float32)


@pytest.fixture
def fake_models(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(models, "resolve_dir", lambda cfg: tmp_path)
    monkeypatch.setattr(models, "fingerprint", lambda d: "model-A")
    monkeypatch.setattr(engine, "Kokoro", StubKokoro)
    StubKokoro.calls = 0


# --- T5 cache ----------------------------------------------------------------------------------------


def test_cache_key_depends_on_every_rendering_input() -> None:
    base = worker.cache_key(U, U.text, "model-A", 1.0)
    assert worker.cache_key(U, U.text, "model-A", 1.0) == base
    variants = [
        worker.cache_key(U, "other text", "model-A", 1.0),
        worker.cache_key(replace(U, voice="bf_emma"), U.text, "model-A", 1.0),
        worker.cache_key(replace(U, speed=1.0), U.text, "model-A", 1.0),
        worker.cache_key(replace(U, pitch_st=1.0), U.text, "model-A", 1.0),
        worker.cache_key(replace(U, mood="sorry"), U.text, "model-A", 1.0),
        worker.cache_key(replace(U, earcon=False), U.text, "model-A", 1.0),
        worker.cache_key(U, U.text, "model-B", 1.0),
        worker.cache_key(U, U.text, "model-A", 0.5),
    ]
    assert len(set(variants)) == len(variants) and base not in variants


def test_render_miss_then_hit(cfg: dict[str, Any], fake_models: None) -> None:
    p1, i1 = worker.render(U, cfg)
    p2, i2 = worker.render(U, cfg)
    assert (i1["cache"], i2["cache"]) == ("miss", "hit") and p1 == p2 and StubKokoro.calls == 1
    y, sr = sf.read(p1)
    assert sr == engine.SR and len(y) > 2400  # earcon + gap + speech
    assert float(np.max(np.abs(y))) <= 0.99


def test_respelling_reaches_the_engine_only(cfg: dict[str, Any], fake_models: None) -> None:
    cfg["respell"] = {"alpha": "al fa"}
    _, info = worker.render(U, cfg)
    assert info["spoken_text"] == "Ada, the results of al fa landed."


def test_render_without_models_fails(cfg: dict[str, Any]) -> None:
    with pytest.raises(models.ModelError):
        worker.render(U, cfg)


# --- speak: fallback, queue timeout, log ------------------------------------------------------------------


def test_speak_plays_and_logs(cfg: dict[str, Any], fake_models: None, tmp_path: Path) -> None:
    marks = tmp_path / "marks"
    cfg["player"] = fake_player(tmp_path, marks, 0.0)
    rec = worker.speak(U, cfg)
    assert rec["outcome"] == "played" and rec["player"] == cfg["player"]
    assert marks.read_text().count("start") == 1
    assert journal.tail(1)[0]["text"] == U.text


def test_speak_falls_back_to_the_system_voice(cfg: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    said: list[tuple[str, str]] = []

    def fake(text: str, lang: str) -> str:
        said.append((text, lang))
        return "spd-say"

    monkeypatch.setattr(player, "fallback_speak", fake)
    rec = worker.speak(U, cfg)
    assert rec["outcome"] == "spoken" and rec["engine"] == "spd-say" and "ModelError" in rec["engine_error"]
    assert said == [(U.text, "en")]


def test_speak_reports_every_failure(cfg: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(text: str, lang: str) -> str:
        raise player.PlayerError("no fallback voice")

    monkeypatch.setattr(player, "fallback_speak", broken)
    rec = worker.speak(U, cfg)
    assert rec["outcome"].startswith("error: PlayerError")
    assert journal.tail(1)[0]["outcome"] == rec["outcome"]


def test_queue_timeout(cfg: dict[str, Any]) -> None:
    lock = paths.state_dir() / "speak.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        rec = worker.speak(U, cfg, lock_timeout=0.2)
    assert rec["outcome"] == "dropped: queue timeout"


# --- T4 serialization across processes ---------------------------------------------------------------------


def _speak_in_child(u_json: str, cfg_json: str) -> None:
    worker.speak(Utterance.from_json(u_json), json.loads(cfg_json))


def test_speech_is_serialized(cfg: dict[str, Any], fake_models: None, tmp_path: Path) -> None:
    marks = tmp_path / "marks"
    cfg["player"] = fake_player(tmp_path, marks, 0.3)
    worker.render(U, cfg)  # warm the cache: children only lock and play
    ctx = mp.get_context("fork")
    children = [ctx.Process(target=_speak_in_child, args=(U.to_json(), json.dumps(cfg))) for _ in range(3)]
    for c in children:
        c.start()
    for c in children:
        c.join(10)
    events = sorted((float(t), kind) for kind, t in (line.split() for line in marks.read_text().splitlines()))
    assert [k for _, k in events] == ["start", "end"] * 3, events  # never two "start" in a row
