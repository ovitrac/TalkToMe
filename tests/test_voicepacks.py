"""Downloadable packs (design §7.3): pinned voices, verified download, Piper engine, German end to end.

No network and no Piper model: downloads, voices and the engine are replaced by local fakes.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import hashlib
import random
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from talktome import cli, config, engine, fun, langs, models, voicepacks, worker
from talktome.decide import Event, Utterance, decide
from talktome.state import SessionState

FAKE = "xx_XX-test-low"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def fake_voice(monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    """One small voice in place of the German ones; returns the content of its two files."""
    content = {".onnx": b"model bytes", ".onnx.json": b'{"audio": {}}'}
    info = {
        "gender": "f",
        "path": "xx/xx_XX/test/low/" + FAKE,
        "license": "CC0",
        "onnx": {"size": len(content[".onnx"]), "sha256": _sha(content[".onnx"])},
        "json": {"size": len(content[".onnx.json"]), "sha256": _sha(content[".onnx.json"])},
    }
    monkeypatch.setattr(voicepacks, "voices", lambda code: {FAKE: info})
    return content


def _serve(monkeypatch: pytest.MonkeyPatch, content: dict[str, bytes], urls: list[str]) -> None:
    def urlretrieve(url: str, dest: Path) -> None:
        urls.append(url)
        ext = ".onnx.json" if url.endswith(".json") else ".onnx"
        Path(dest).write_bytes(content[ext])

    monkeypatch.setattr("urllib.request.urlretrieve", urlretrieve)


# --- pinned files, download, verification --------------------------------------------------------------


def test_german_files_are_pinned() -> None:
    fs = voicepacks.files("de")
    assert len(fs) == 4 and voicepacks.download_size("de") == 126_314_797
    base = langs.pack("de")["piper"]["base_url"]
    assert all(url.startswith(base) and url.endswith((".onnx", ".onnx.json")) for url, _, _, _ in fs)
    assert all(dest.parent == voicepacks.voice_dir() for _, dest, _, _ in fs)
    assert len(voicepacks.missing("de")) == 4


def test_download_verifies_and_installs(
    monkeypatch: pytest.MonkeyPatch, fake_voice: dict[str, bytes]
) -> None:
    urls: list[str] = []
    _serve(monkeypatch, fake_voice, urls)
    assert voicepacks.download("de", progress=lambda s: None) == [f"{FAKE}.onnx", f"{FAKE}.onnx.json"]
    assert len(urls) == 2 and voicepacks.missing("de") == [] and voicepacks.verify("de") == []
    assert voicepacks.download("de", progress=lambda s: None) == []  # nothing left to fetch
    assert not list(voicepacks.voice_dir().glob("*.part"))


def test_download_refuses_a_different_file(
    monkeypatch: pytest.MonkeyPatch, fake_voice: dict[str, bytes]
) -> None:
    _serve(monkeypatch, {".onnx": b"model BYTES", ".onnx.json": fake_voice[".onnx.json"]}, [])
    with pytest.raises(models.ModelError, match="SHA-256"):
        voicepacks.download("de", progress=lambda s: None)
    assert not (voicepacks.voice_dir() / f"{FAKE}.onnx").exists()
    assert not list(voicepacks.voice_dir().glob("*.part"))


def test_fingerprint_hashes_once_then_detects_changes(
    monkeypatch: pytest.MonkeyPatch, fake_voice: dict[str, bytes]
) -> None:
    with pytest.raises(models.ModelError, match="lang add de"):
        voicepacks.fingerprint("de", FAKE)
    _serve(monkeypatch, fake_voice, [])
    voicepacks.download("de", progress=lambda s: None)
    fp = voicepacks.fingerprint("de", FAKE)
    assert fp == f"piper:{FAKE}:{_sha(fake_voice['.onnx'])[:12]}:0.0"  # no measured floor
    calls: list[Path] = []
    real = models.sha256
    monkeypatch.setattr(models, "sha256", lambda p: calls.append(p) or real(p))
    assert voicepacks.fingerprint("de", FAKE) == fp and calls == []  # stat record trusted
    (voicepacks.voice_dir() / f"{FAKE}.onnx").write_bytes(b"model bytez")  # same size, other content
    with pytest.raises(models.ModelError, match="SHA-256"):
        voicepacks.fingerprint("de", FAKE)
    with pytest.raises(models.ModelError, match="not a voice"):
        voicepacks.fingerprint("de", "de_DE-nobody-low")


def test_remove(monkeypatch: pytest.MonkeyPatch, fake_voice: dict[str, bytes]) -> None:
    _serve(monkeypatch, fake_voice, [])
    voicepacks.download("de", progress=lambda s: None)
    assert len(voicepacks.remove("de")) == 2 and voicepacks.remove("de") == []
    assert len(voicepacks.missing("de")) == 2


# --- engine --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("sr", [16000, 22050, 24000])
def test_resample_to_24k(sr: int) -> None:
    y = np.sin(2 * np.pi * 200 * np.arange(sr) / sr).astype(np.float32)  # 1 s at 200 Hz
    z = engine.resample(y, sr)
    assert len(z) == engine.SR and z.dtype == np.float32
    crossings = int(np.sum(np.diff(np.signbit(z).astype(int)) != 0))
    assert crossings == pytest.approx(400, abs=2)  # still 200 Hz


@dataclass
class _Chunk:
    sample_rate: int
    audio_float_array: np.ndarray


def _fake_piper(monkeypatch: pytest.MonkeyPatch, seen: dict[str, Any]) -> None:
    class SynthesisConfig:
        def __init__(self, length_scale: float | None = None) -> None:
            self.length_scale = length_scale

    class Voice:
        config = types.SimpleNamespace(length_scale=1.1, phoneme_id_map={"ɪ": [1], "ç": [2], "c": [3]})

        @classmethod
        def load(cls, model: Path, config_path: Path) -> Voice:
            seen["load"] = (model, config_path)
            return cls()

        def phonemize(self, text: str) -> list[list[str]]:
            return [["ɪ", "c", "\u0327"]]  # "ich", decomposed as Piper 1.8 does

        def synthesize(self, text: str, syn_config: SynthesisConfig) -> list[_Chunk]:
            seen["phonemes"] = self.phonemize(text)
            seen["length_scale"] = syn_config.length_scale
            half = np.full(11025, 0.25, dtype=np.float32)
            return [_Chunk(22050, half), _Chunk(22050, half)]

    mod = types.ModuleType("piper")
    mod.PiperVoice = Voice  # type: ignore[attr-defined]
    mod.SynthesisConfig = SynthesisConfig  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "piper", mod)


def test_piper_engine_scales_its_own_length_and_resamples(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}
    _fake_piper(monkeypatch, seen)
    y = engine.Piper(Path("m.onnx"), Path("m.onnx.json"), floor=0.5).synth("ich", 1.25, 0.0)
    assert seen["load"] == (Path("m.onnx"), Path("m.onnx.json"))
    assert seen["length_scale"] == pytest.approx((1.1 + 0.5) / 1.25 - 0.5)
    assert seen["phonemes"] == [["ɪ", "ç"]]  # the voice knows ç, not the combining cedilla
    assert len(y) == engine.SR  # two chunks of 0.5 s at 22.05 kHz → 1 s at 24 kHz
    engine.Piper(Path("m.onnx"), Path("m.onnx.json")).synth("ich", 1.0, 2.0)
    assert seen["length_scale"] == pytest.approx(1.1 / engine.synth_speed(1.0, 2.0))


@pytest.mark.parametrize("floor", [0.0, 0.46, 0.68])
def test_length_scale_gives_the_asked_speed_under_the_duration_model(floor: float) -> None:
    def duration(ls: float) -> float:  # D(ls) ∝ ls + floor (design §7.3)
        return ls + floor

    for speed in (0.85, 1.2, 1.5):
        ls = engine.length_scale(1.0, floor, speed)
        assert duration(1.0) / duration(ls) == pytest.approx(speed)
    assert engine.length_scale(1.0, 0.68, 2.0) == engine.MIN_LENGTH_SCALE


def test_recompose_only_when_the_voice_lacks_the_mark() -> None:
    nfd = ["n", "ɪ", "c", "\u0327", "t"]
    assert engine.recompose(nfd, {"ç": [1]}) == ["n", "ɪ", "ç", "t"]
    assert engine.recompose(nfd, {"ç": [1], "\u0327": [2]}) == nfd  # trained on decomposed phonemes
    assert engine.recompose(nfd, {}) == nfd  # nothing better to offer: Piper reports it


# --- German through the worker, decide and fun ---------------------------------------------------------


def test_worker_renders_german_with_piper(monkeypatch: pytest.MonkeyPatch, cfg: dict[str, Any]) -> None:
    calls: list[tuple[str, float, float]] = []

    class StubPiper:
        def __init__(self, model: Path, config_path: Path, floor: float) -> None:
            assert model.name == "de_DE-thorsten-medium.onnx" and floor == 0.46

        def synth(self, text: str, speed: float, pitch: float) -> np.ndarray:
            calls.append((text, speed, pitch))
            return np.zeros(2400, dtype=np.float32)

    monkeypatch.setattr(voicepacks, "fingerprint", lambda code, v: f"piper:{v}:abc")
    monkeypatch.setattr(engine, "Piper", StubPiper)
    monkeypatch.setattr(models, "resolve_dir", lambda c: pytest.fail("Kokoro models are not needed"))
    u = Utterance(
        "s",
        "Merlin",
        "stop",
        "landed",
        "useful",
        "de",
        "Ada, die Ergebnisse von Merlin sind da.",
        "neutral",
        "de_DE-thorsten-medium",
        1.0,
        0.0,
        False,
    )
    path, info = worker.render(u, cfg)
    assert info["engine"] == "piper" and info["cache"] == "miss" and path.is_file() and len(calls) == 1
    assert worker.render(u, cfg)[1]["cache"] == "hit" and len(calls) == 1


@pytest.mark.parametrize("register", ["useful", "fun"])
@pytest.mark.parametrize(
    "cwd, voice", [("/w/Merlin", "de_DE-thorsten-medium"), ("/w/die Maschine", "de_DE-kerstin-low")]
)
def test_german_alert(cfg: dict[str, Any], register: str, cwd: str, voice: str) -> None:
    c = {**cfg, "language": "de", "languages": [*cfg["languages"], "de"], "register": register}
    assert config.validate(c) == []
    e = Event(kind="pretool", tool_name="AskUserQuestion", cwd=cwd)
    u = decide(e, SessionState(), c, 100.0, random.Random(0)).utterance
    assert u is not None and u.lang == "de" and u.voice == voice and "Ada" in u.text


def test_german_why_and_fun() -> None:
    for seed in range(200):
        text = fun.why("de", random.Random(seed))
        assert "{" not in text and "  " not in text and text[0].isupper()
    assert fun.why("de", random.Random(7)) == fun.why("de", random.Random(7))
    assert len(fun.items("joke", "de")) >= 10 and len(fun.items("fact", "de")) == len(fun.items("fact", "en"))


# --- configuration -------------------------------------------------------------------------------------


def test_german_voice_overrides(cfg: dict[str, Any]) -> None:
    c = config.set_value(cfg, "voices.de", "de_DE-kerstin-low")
    assert config.voice_for(c, "de", "m") == "de_DE-kerstin-low"
    for key, value, why in (
        ("voices.de", "bf_emma", "not a voice of the de pack"),
        ("voices.de", "de_DE-nobody-medium", "not a voice of the de pack"),
        ("voices.en", "de_DE-kerstin-low", "Piper voice"),
    ):
        with pytest.raises(config.ConfigError, match=why):
            config.set_value(cfg, key, value)
    assert config.validate({**cfg, "voices": {"de": "de_DE-nobody-medium"}}) == []  # shape only: hook path
    assert config.voice_errors({**cfg, "voices": {"de": "de_DE-nobody-medium"}})


# --- command line --------------------------------------------------------------------------------------


@pytest.fixture
def sparse_fetch(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Pretend downloads: sparse files of the pinned size (enough for `missing`)."""
    fetched: list[str] = []

    def fetch_file(url: str, dest: Path, size: int, sha256: str) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            f.truncate(size)
        fetched.append(dest.name)

    monkeypatch.setattr(voicepacks, "fetch_file", fetch_file)
    monkeypatch.setattr(voicepacks, "engine_available", lambda: True)
    return fetched


def test_lang_add_needs_the_engine(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cli.main(["setup", "--no-link"])
    monkeypatch.setattr(voicepacks, "engine_available", lambda: False)
    assert cli.main(["lang", "add", "de"]) == 2
    assert "pipx inject talktome piper-tts" in capsys.readouterr().err
    assert "de" not in config.load()["languages"] and voicepacks.missing("de")


def test_lang_add_failed_download_installs_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cli.main(["setup", "--no-link"])
    monkeypatch.setattr(voicepacks, "engine_available", lambda: True)

    def fail(*a: Any) -> None:
        raise models.ModelError("size or SHA-256 differs from the pinned value")

    monkeypatch.setattr(voicepacks, "fetch_file", fail)
    assert cli.main(["lang", "add", "de"]) == 2
    assert "nothing installed" in capsys.readouterr().err and "de" not in config.load()["languages"]


def test_lang_add_list_voices_remove_purge(
    sparse_fetch: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    cli.main(["setup", "--no-link"])
    assert cli.main(["setup", "--no-link", "--language", "de"]) == 2  # download first
    capsys.readouterr()
    assert cli.main(["lang"]) == 0 and "126 MB to download" in capsys.readouterr().out
    assert cli.main(["lang", "add", "de"]) == 0 and len(sparse_fetch) == 4
    assert "de" in config.load()["languages"] and "verified" in capsys.readouterr().out
    assert cli.main(["lang", "add", "de"]) == 0 and len(sparse_fetch) == 4  # nothing fetched again
    assert cli.main(["lang"]) == 0 and "piper, downloaded" in capsys.readouterr().out
    assert cli.main(["voices", "--lang", "de"]) == 0
    listing = capsys.readouterr().out
    assert "de_DE-kerstin-low  (f, CC0" in listing and "not downloaded" not in listing
    assert cli.main(["set", "language", "de"]) == 0
    assert cli.main(["lang", "remove", "de"]) == 2  # the language in use
    assert cli.main(["set", "language", "en"]) == 0
    capsys.readouterr()
    assert cli.main(["lang", "remove", "de"]) == 0 and "--purge" in capsys.readouterr().out
    assert not voicepacks.missing("de")  # kept
    assert (
        cli.main(["lang", "remove", "de", "--purge"]) == 0
        and "4 voice files deleted" in capsys.readouterr().out
    )
    assert len(voicepacks.missing("de")) == 4
