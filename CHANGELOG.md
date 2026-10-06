# Changelog

All notable changes to TalkToMe are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Author:** Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr

## [Unreleased]

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
