# TalkToMe

Spoken alerts from concurrent Claude Code sessions — local text-to-speech, English or French, configurable voice
and mood.

> *"Hi Olivier, I need your help on…"* · *"The results of [THIS SESSION] landed."*

**Status:** v0.1.0 — speech, command line, Claude Code hooks, plugin and `/talktome` skill. Design:
`base/DESIGN_TALKTOME_20261006.md`; decisions: `base/DECISIONS.md`; changes: `CHANGELOG.md`.

## Intent

When you work with several Claude Code sessions at once, each session can call you by voice when it needs your
help, needs your attention, or has finished a long piece of work, and tells you which session is speaking.

- Local-first: speech is synthesized on your machine (Kokoro-82M through `kokoro-onnx`); no cloud service, no
  network at runtime.
- English by default, French available; voice, speed, addressee name and mood are configurable.
- Short templated messages only by default: nothing from your transcript is read aloud.
- Never slows down or breaks a Claude Code session.

## Install

TalkToMe has two parts: the speaking engine (a Python package) and the Claude Code plugin (hooks and the
`/talktome` skill). The plugin is published in the **adservio** marketplace, where it can be installed alone or
with the other Adservio tools.

1. The speaking engine (Python ≥ 3.11, Linux or macOS):

   ```bash
   pipx install git+https://github.com/ovitrac/TalkToMe@v0.1.0
   talktome setup --name "Your name" --fetch   # Kokoro model files, 338 MB, SHA-256 checked
   talktome doctor
   ```

   Already have `kokoro-v1.0.onnx` and `voices-v1.0.bin`? Use `talktome setup --models-dir DIR` instead of
   `--fetch`.

2. The Claude Code plugin, from inside Claude Code:

   ```text
   /plugin marketplace add ovitrac/AdservioToolbox
   /plugin install talktome@adservio
   ```

   `adservio-toolbox@adservio` installs TalkToMe together with the other Adservio tools instead
   (see [AdservioToolbox](https://github.com/ovitrac/AdservioToolbox)).

## What you hear

| When | English (*useful*) |
|---|---|
| a session asks you a question or shows a plan | "Ada, alpha needs your help." |
| a session asks for a permission | "Ada, alpha needs your attention." |
| a session waits for you (reminder, at most every 5 min) | "Ada, alpha needs your input." |
| a turn of 60 s or more has finished | "Ada, the results of alpha landed." |

Each session is a *he* or a *she*, never an *it*: the gender is improvised from the session's name, as a
native speaker would guess it (Hermes, *le moteur* → he; Ariadne, *la chaise* → she), and picks a male or
female English voice; `talktome gender f|m` overrides it. The *fun* register rotates natural variations; French
uses *tu* and one voice. Each message opens with a short chime that
carries its mood. Sessions speak one at a time.

## Tune it

```bash
talktome test                          # hear a sample
talktome set language fr               # or en
talktome set register fun              # or useful
talktome set voices.en bf_emma         # talktome voices --lang en
talktome set speed.en 1.2              # per language
talktome name "Data cleaning"          # spoken name of the current session
talktome gender f                      # or m; auto to improvise again
talktome mute 30                       # minutes; `talktome unmute`
```

Inside Claude Code: `/talktome fr`, `/talktome fun`, `/talktome voice bf_emma`, `/talktome mute 30`. Everything
lives in `~/.config/talktome/config.json`; every utterance is logged in `~/.local/state/talktome/log.jsonl`.

## License

MIT — see `LICENSE`.

**Author:** Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
