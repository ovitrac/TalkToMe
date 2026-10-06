# Changelog

All notable changes to TalkToMe are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Author:** Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr

## [Unreleased]

## [0.4.0] — 2026-10-06

### Added

- **Downloadable language packs** spoken by [Piper](https://github.com/OHF-Voice/piper1-gpl):
  `talktome lang add de` downloads the pack's voices (pinned by size and SHA-256 at a fixed revision; nothing
  unverified is kept) and installs the language. First pack: **German** (*du*), with two CC0 voices,
  `de_DE-thorsten-medium` (male) and `de_DE-kerstin-low` (female), 126 MB.
- The Piper engine (`piper-tts`, GPL-3.0) is optional and never bundled: `pipx inject talktome piper-tts`, or the
  extra `talktome[piper]`. Without it, `lang add de` says what to run.
- `talktome lang remove CODE --purge` deletes downloaded voices; `lang list` shows the download size;
  `voices --lang de` lists a pack's voices with their license; `doctor` re-hashes the installed voices.
- Piper speaks at the requested speed: a measured per-voice duration floor corrects Piper's length scale
  (asked 1.5, measured 1.45–1.52; without it 1.14–1.20).

### Fixed

- German *ich*-laut with `piper-tts` 1.8: the decomposed `ç` is recomposed for voices that only know `ç`
  (*nicht* was spoken *nict*).

## [0.3.0] — 2026-10-06

### Added

- **Language packs** (`src/talktome/lang/<code>.toml`): alerts (sober and playful), jokes, facts, `why`, voices,
  grammar (articles, elision, contractions) and the gender cues of one language. Installed by default: English,
  French, Spanish, Portuguese (Brazil), Italian; experimental (pronunciation not reviewed): Hindi, Mandarin. All
  speak through the Kokoro voices already installed — no extra download.
- **`talktome lang [list | add CODE | remove CODE]`**; `talktome set language CODE` accepts installed languages.
- Native jokes and the same fifteen facts in every stable language; `why` with agreeing articles and adjectives
  (Spanish "al", Italian "l'"/"lo").

### Changed

- The templates, jokes, facts and `why` lists moved from `catalog.toml` and `fun.toml` into the language packs.
- Configuration: `languages` (installed packs); `voices` and `speed` are optional overrides per language (the
  packs give the defaults). Files written by 0.2.0 load unchanged.
- Audio cache keys include the language (cache version 2).

### Not included

- Japanese: Kokoro's built-in phonemizer reads kanji as the English words "Japanese letter"; correct Japanese
  needs an extra phonemizer.
- German, European Portuguese and other Piper languages: next release.

## [0.2.0] — 2026-10-06

### Added

- **Per-session modes**: `on` (default), `discreet` (alerts without the session's name — "a session" / "une
  session" — and no free text; jokes, facts and `why` still allowed), `off` (silent). Set inside the session
  (`talktome mode on|discreet|off|auto`, `/talktome off`), at launch (`TALKTOME=off claude`), or by folder in the
  configuration (`private`: `{"~/clients/*": "discreet"}`; empty by default). The log never records the name of a
  discreet or silent session.
- **`talktome joke`** and **`talktome fact`**: a joke or a surprising fact in the configured language, never the
  same until all have been told.
- **`talktome why [N]`**: an answer to "why?", in the spirit of MATLAB's `why`; the same seed gives the same
  answer.
- **macOS**: `afplay` as a player and the system `say` as the fallback voice (untested on a Mac).

### Fixed

- French elision: "les résultats d'Atlas", "parce qu'Ada" (was "de Atlas").
- A sentence that starts with the session's name now starts with a capital letter.

### Removed

- Standalone marketplace manifest (`.claude-plugin/marketplace.json`): TalkToMe is distributed through the
  **adservio** marketplace (`/plugin marketplace add ovitrac/AdservioToolbox`, then
  `/plugin install talktome@adservio`).

## [0.1.0] — 2026-10-06

First release.

### Added

- **Spoken alerts** from Claude Code sessions: *help* (a question or a plan waiting), *attention* (a permission
  prompt), *input* (waiting for you, a reminder at most every 5 min), *landed* (a turn of 60 s or more has
  finished). Debounce, cooldown and mute; every decision and utterance logged as JSON lines.
- **Two registers**: *useful* (one sober sentence per alert) and *fun* (rotating natural variations); English
  (default) and French (*tu*).
- **Moods**: neutral, warm, calm, cheerful, firm, urgent, sorry — speed, pitch shift with speed compensation,
  and a synthesized chime per mood.
- **Sessions are he or she, never it**: gender improvised from the session's name (French article, known names,
  French noun endings, final letter, stable hash), overridable; the English voice and *his*/*her* follow it.
- **Local speech**: Kokoro-82M through `kokoro-onnx` (model files verified by SHA-256), voice blends, per-language
  voice and speed, audio cache, one voice at a time across sessions; `spd-say` fallback.
- **Command line** `talktome`: `setup`, `doctor`, `say`, `test`, `name`, `gender`, `set`, `show`, `voices`,
  `mute`, `unmute`, `hook`.
- **Claude Code plugin**: hooks on UserPromptSubmit, PreToolUse, Notification and Stop through a wrapper that
  never blocks or alters a session; `/talktome` skill for deliberate messages and settings.
