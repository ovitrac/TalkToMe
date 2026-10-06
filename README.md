# TalkToMe

Spoken alerts from concurrent Claude Code sessions — local text-to-speech, English or French, configurable voice
and mood.

> *"Hi Olivier, I need your help on…"* · *"The results of [THIS SESSION] landed."*

**Status:** v0.1 in development — speech and command line work (`talktome say`, `test`, `doctor`); the Claude
Code hooks and plugin come next. Design: `base/DESIGN_TALKTOME_20261006.md`; decisions: `base/DECISIONS.md`.

## Intent

When you work with several Claude Code sessions at once, each session can call you by voice when it needs your
help, needs your attention, or has finished a long piece of work, and tells you which session is speaking.

- Local-first: speech is synthesized on your machine (Kokoro-82M through `kokoro-onnx`); no cloud service, no
  network at runtime.
- English by default, French available; voice, speed, addressee name and mood are configurable.
- Short templated messages only by default: nothing from your transcript is read aloud.
- Never slows down or breaks a Claude Code session.

## License

MIT — see `LICENSE`.

**Author:** Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
