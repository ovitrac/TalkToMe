# Changelog

All notable changes to TalkToMe are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Author:** Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr

## [Unreleased]

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
