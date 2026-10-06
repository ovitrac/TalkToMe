# TalkToMe

Spoken alerts from concurrent Claude Code sessions — local text-to-speech, English or French, configurable voice
and mood.

> *"Hi Olivier, I need your help on…"* · *"The results of [THIS SESSION] landed."*

**Status:** v0.4.0 — speech, command line, Claude Code hooks, plugin and `/talktome` skill, per-session modes,
language packs, downloadable German. Design:
`base/DESIGN_TALKTOME_20261006.md`; decisions: `base/DECISIONS.md`; changes: `CHANGELOG.md`.

## Intent

When you work with several Claude Code sessions at once, each session can call you by voice when it needs your
help, needs your attention, or has finished a long piece of work, and tells you which session is speaking.

- Local-first: speech is synthesized on your machine (Kokoro-82M through `kokoro-onnx`); no cloud service, no
  network at runtime.
- English by default; French, Spanish, Portuguese, Italian (and Hindi, Mandarin, experimental) built in;
  German as a download. Voice, speed, addressee name and mood are configurable.
- Short templated messages only by default: nothing from your transcript is read aloud.
- Never slows down or breaks a Claude Code session.

## Install

TalkToMe has two parts: the speaking engine (a Python package) and the Claude Code plugin (hooks and the
`/talktome` skill). The plugin is published in the **adservio** marketplace, where it can be installed alone or
with the other Adservio tools.

1. The speaking engine (Python ≥ 3.11; Linux; macOS should work through `afplay` but is untested):

   ```bash
   pipx install git+https://github.com/ovitrac/TalkToMe@v0.3.0
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
talktome mute 30                       # minutes, every session; `talktome unmute`
talktome joke                          # a joke; also: talktome fact, talktome why
```

## Languages

| Code | Language | Voices (female / male) | Status |
|---|---|---|---|
| `en` | English | 3 / 3 (pool) | default |
| `fr` | Français | 1 voice for everyone | default |
| `es` | Español | 1 / 2 | default |
| `pt` | Português (Brasil) | 1 / 2 | default |
| `it` | Italiano | 1 / 1 | default |
| `hi` | हिन्दी (Hindi) | 2 / 2 | experimental |
| `zh` | 中文 (Mandarin) | 4 / 4 | experimental |
| `de` | Deutsch | 1 / 1 (Piper, CC0) | download, 126 MB |

```bash
talktome lang                          # installed and available packs
talktome set language es               # or /talktome es inside Claude Code
talktome lang remove zh                # or: talktome lang add zh
```

The built-in packs use the Kokoro voices already installed. Experimental packs have not been reviewed by native
speakers.

**Downloadable packs.** German speaks with [Piper](https://github.com/OHF-Voice/piper1-gpl) voices, downloaded
once and checked against their pinned SHA-256. Piper (GPL-3.0) is optional and installed separately:

```bash
pipx inject talktome piper-tts         # or, in a virtual environment: pip install 'talktome[piper]'
talktome lang add de                   # downloads two CC0 voices (126 MB), then installs German
talktome set language de
talktome lang remove de --purge        # uninstall and delete the voices
```

## Confidential sessions

TalkToMe never reads your conversation aloud, but it does say the session's name — often a client's name.
Each session has a mode:

| Mode | What you hear |
|---|---|
| `on` (default) | as above |
| `discreet` | the alerts, without the name: "Ada, a session needs your help."; no free text from Claude |
| `off` | nothing |

Set it inside a session (`/talktome off`, `/talktome discreet`, `/talktome on`), at launch
(`TALKTOME=discreet claude`), or for whole folders in `~/.config/talktome/config.json`:

```json
"private": { "~/clients/*": "discreet" }
```

Inside Claude Code: `/talktome fr`, `/talktome fun`, `/talktome voice bf_emma`, `/talktome mute 30`,
`/talktome joke`, `/talktome fact`, `/talktome why`. Everything
lives in `~/.config/talktome/config.json`; every utterance is logged in `~/.local/state/talktome/log.jsonl`.

## License

MIT — see `LICENSE`.

**Author:** Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
