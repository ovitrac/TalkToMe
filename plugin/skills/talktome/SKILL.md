---
name: talktome
description: Speak to the user out loud through TalkToMe, and change how TalkToMe speaks. Use when the user asks to be told by voice ("tell me when it's done", "talk to me", "speak to me"), asks TalkToMe for a joke, a surprising fact or a "why", when a long task the user is not watching ends with an outcome they should hear (a failure especially), or when the user asks to change TalkToMe's language, register, voice, speed, mood, session name or mode (on, discreet, off), or to mute it — including /talktome with arguments such as "fr", "fun", "off", "discreet", "joke", "why", "voice bf_emma", "speed 1.2", "mute 30".
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
  uses *tu*, Spanish *tú*, Portuguese *você*, Italian *tu*). Write `{name}` to address the user and `{session}` for this session's spoken name; TalkToMe fills
  both. Example: `talktome say --mood sorry "{name}, the build failed on {session}. Two tests are red."`
- **Mood.** `neutral`, `warm`, `calm`, `cheerful`, `firm`, `urgent`, `sorry` — pick the one that fits the
  outcome.
- **Never** speak secrets, `TAG-…` placeholders, file paths, code, command output or quoted content: anyone in
  the room hears it. TalkToMe refuses placeholders and texts over 280 characters.
- **Sessions are people.** Each session is "he" or "she", never "it"; write `{his}` and TalkToMe fills
  *his* or *her* from the session's gender.
- A deliberate message replaces the automatic "results landed" alert of the same turn.
- **Confidential sessions.** In a `discreet` session TalkToMe refuses free text (`say`): do not retry, and do not
  move the content into a joke or a fact. In an `off` session nothing is spoken.

## Settings: `/talktome ARGUMENTS`

Run the matching command, then report the result in one line.

| Arguments | Command |
|---|---|
| `en`, `fr`, `es`, `pt`, `it`, `hi`, `zh`, `de` | `talktome set language CODE` (an installed language; see `talktome lang`) |
| `lang`, `lang add CODE`, `lang remove CODE` | `talktome lang`, `talktome lang add CODE`, `talktome lang remove CODE` — `add de` downloads 126 MB of voices: confirm with the user first; if Piper is missing, relay the install command it prints |
| `useful`, `fun` | `talktome set register useful` (or `fun`) |
| `voice NAME` | `talktome set voices.LANG.G NAME` (current language; G = the voice's gender: second letter of a Kokoro name, `bf_emma` → f, `bm_lewis` → m; for a Piper voice such as `de_DE-kerstin-low`, the gender `talktome voices --lang LANG` shows) |
| `speed X` | `talktome set speed.LANG X` with the current language (0.5–2.0) |
| `mood CLASS MOOD` | `talktome set moods.CLASS MOOD` (classes: help, attention, input, landed) |
| `name TEXT` | `talktome name "TEXT" --gender f\|m` — this session's spoken name (see below) |
| `gender f\|m\|auto` | `talktome gender f` (or `m`; `auto` lets TalkToMe improvise again) |
| `mute [MINUTES]`, `unmute` | `talktome mute [MINUTES]`, `talktome unmute` — every session |
| `off`, `discreet`, `on` | `talktome mode off` (or `discreet`, `on`; `auto` follows the launch value and folder rules again) — this session only |
| `joke`, `fact` | `talktome joke`, `talktome fact` — a joke or a surprising fact, in the configured language |
| `why [N]` | `talktome why [N]` — an answer to "why?", like MATLAB's `why` |
| `test` | `talktome test` — plays a sample now |
| `say TEXT` | `talktome say "TEXT"` |
| `status` or nothing | `talktome doctor` |

## Gender of a session

The gender sets the English voice (female or male) and *his* / *her*; French has one voice. When you name a
session, give it the gender a native speaker would hear: given names by usage (Hermes → m, Ariadne → f), things
by their French grammatical gender (a chair → la chaise → f; an engine → le moteur → m). If nothing comes to
mind, omit `--gender`: TalkToMe improvises from the spelling and keeps that choice for the name.

If `talktome` is not found, the Python package is missing: tell the user to run
`pipx install git+https://github.com/ovitrac/TalkToMe` and then `talktome setup --fetch`.
