---
name: talktome
description: Speak to the user out loud through TalkToMe, and change how TalkToMe speaks. Use when the user asks to be told by voice ("tell me when it's done", "talk to me", "speak to me"), when a long task the user is not watching ends with an outcome they should hear (a failure especially), or when the user asks to change TalkToMe's language, register, voice, speed, mood or session name, or to mute it — including /talktome with arguments such as "fr", "fun", "voice bf_emma", "speed 1.2", "mute 30".
user-invocable: true
argument-hint: "[say <text> | en | fr | useful | fun | voice <name> | speed <x> | name <text> | mute [min] | unmute | test | status]"
allowed-tools:
  - Bash(talktome *)
---

# TalkToMe

TalkToMe speaks through the `talktome` command on the user's machine (local text-to-speech). The automatic
alerts (a question or plan waiting, a permission prompt, waiting for input, a long turn finished) come from this
plugin's hooks. This skill is for **deliberate messages** and **settings**.

## Speaking deliberately

```bash
talktome say [--mood MOOD] "TEXT"
```

It returns at once; the speech is queued behind other sessions.

- **When.** Only when it helps a user who is not watching: they asked to be told, or a long task ended with an
  outcome they should hear (a failure, a decision to take, a notable result). Never narrate routine progress. At
  most one message per turn.
- **What.** One or two short, natural sentences in the configured language (`talktome show` → `language`; French
  uses *tu*). Write `{name}` to address the user and `{session}` for this session's spoken name; TalkToMe fills
  both. Example: `talktome say --mood sorry "{name}, the build failed on {session}. Two tests are red."`
- **Mood.** `neutral`, `warm`, `calm`, `cheerful`, `firm`, `urgent`, `sorry` — pick the one that fits the
  outcome.
- **Never** speak secrets, `TAG-…` placeholders, file paths, code, command output or quoted content: anyone in
  the room hears it. TalkToMe refuses placeholders and texts over 280 characters.
- A deliberate message replaces the automatic "results landed" alert of the same turn.

## Settings: `/talktome ARGUMENTS`

Run the matching command, then report the result in one line.

| Arguments | Command |
|---|---|
| `en`, `fr` | `talktome set language en` (or `fr`) |
| `useful`, `fun` | `talktome set register useful` (or `fun`) |
| `voice NAME` | `talktome set voices.LANG NAME` with the current language; list: `talktome voices --lang LANG` |
| `speed X` | `talktome set speed.LANG X` with the current language (0.5–2.0) |
| `mood CLASS MOOD` | `talktome set moods.CLASS MOOD` (classes: help, attention, input, landed) |
| `name TEXT` | `talktome name "TEXT"` — this session's spoken name |
| `mute [MINUTES]`, `unmute` | `talktome mute [MINUTES]`, `talktome unmute` |
| `test` | `talktome test` — plays a sample now |
| `say TEXT` | `talktome say "TEXT"` |
| `status` or nothing | `talktome doctor` |

If `talktome` is not found, the Python package is missing: tell the user to run
`pipx install git+https://github.com/ovitrac/TalkToMe` and then `talktome setup --fetch`.
