# DECISIONS — TalkToMe decision registry

**Author:** Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
**Created:** 2026-10-06 · rules in `CLAUDE.md` §6 (append-only; ids never reused; only the lead changes a status;
every closed row carries ≥ 1 evidence pointer)

**Status vocabulary:** `open · proposed · closed · superseded · rejected`

| ID | Subject | Status | Evidence / notes |
|---|---|---|---|
| D-0001 | Sole human authorship; no machine attribution anywhere (commits, PRs, metadata, docs) | closed | Lead's ruling 2026-10-06: *"authorship is imperative, no machine attribution at all"*. `CLAUDE.md` §0.1 |
| D-0002 | Conda env `talktome`, Python 3.11, cloned from the validated TTS env `video-tts` | closed | Lead's ruling 2026-10-06: *"you need a cloned env"*. Created 2026-10-06: Python 3.11.16, onnxruntime 1.30.0. `CLAUDE.md` §0.2 |
| D-0003 | Integration surface: hooks for event alerts + skill for deliberate messages and settings; packaged as a Claude Code plugin | open | Proposal of 2026-10-06 (session discussion); not yet ruled |
| D-0004 | License MIT; public repository `ovitrac/TalkToMe`; default branch `main` | closed | Lead's ruling 2026-10-06: *"MIT, repo ovitrac, ok git init -b main"*. `LICENSE` |
| D-0005 | Message wording EN / FR | open | 2026-10-06: French register ruled — **tutoiement** (*"agree for 'tu'"*). Open: final EN wording; French for *landed* (*sont arrivés* / *sont tombés* / *sont prêts*) |
| D-0006 | Session-naming resolution order (explicit name → agent name → working-directory basename) | open | Proposal of 2026-10-06 |
| D-0007 | Event → message mapping and noise thresholds | open | 2026-10-06: quiet threshold ruled — *landed* is spoken only for turns ≥ **60 s** (*"ok for a quiet threshold of 60s"*). Open: the event mapping itself |
| D-0008 | Registers (*useful* / *fun*) and mood presets; who chooses the mood (event default, Claude via skill, lead override) | open | Request of 2026-10-06. Kokoro has no emotion control (probe in `CLAUDE.md` §0.3); levers: wording, speed, voice / blend, pitch, earcon |
| D-0009 | Public / private boundary: client and private-project names, local paths and business context live only in the gitignored `CLAUDE.local.md`; staged diffs checked against its deny-list | proposed | Raised 2026-10-06 when the repository was ruled public (D-0004). `CLAUDE.md` §0.0 |
