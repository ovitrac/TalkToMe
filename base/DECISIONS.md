# DECISIONS — TalkToMe decision registry

**Author:** Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
**Created:** 2026-10-06 · append-only; ids never reused; only the lead changes a status, and a change appends a
dated note; every closed row carries ≥ 1 evidence pointer

**Status vocabulary:** `open · proposed · closed · superseded · rejected`

| ID | Subject | Status | Evidence / notes |
|---|---|---|---|
| D-0001 | Sole human authorship; no machine attribution anywhere (commits, PRs, metadata, docs) | closed | Lead's ruling 2026-10-06: *"authorship is imperative, no machine attribution at all"* |
| D-0002 | Conda env `talktome`, Python 3.11, cloned from the validated TTS env `video-tts` | closed | Lead's ruling 2026-10-06: *"you need a cloned env"*. Created 2026-10-06: Python 3.11.16, onnxruntime 1.30.0 |
| D-0003 | Integration surface: hooks for event alerts + skill for deliberate messages and settings; packaged as a Claude Code plugin | closed | Proposal of 2026-10-06. 2026-10-06: ruled — hooks + skill *"good to have"*, plugin packaging retained. Design: `base/DESIGN_TALKTOME_20261006.md` |
| D-0004 | License MIT; public repository `ovitrac/TalkToMe`; default branch `main` | closed | Lead's ruling 2026-10-06: *"MIT, repo ovitrac, ok git init -b main"*. `LICENSE`; commit `9798434` |
| D-0005 | Message wording EN / FR | closed | 2026-10-06: French register — **tutoiement** (*"agree for 'tu'"*). 2026-10-06: wording delegated to Claude (*"it is the vocabulary of Claude not mine, u can judge"*); English keeps *landed*; French *useful* renders it **"sont déposés"** (the lead's vocabulary: *produits / codés / déposés*). Templates: design §4 |
| D-0006 | Session naming | closed | 2026-10-06: *"keep simple and tunable"* — name given to the session, else the working-directory basename; per-user respelling map |
| D-0007 | Event → message mapping and noise thresholds | closed | 2026-10-06: quiet threshold ruled — *landed* only for turns ≥ **60 s** (*"ok for a quiet threshold of 60s"*). Mapping, debounce and cooldown: design §3. 2026-10-06: design validated (*"deal to both"*) |
| D-0008 | Registers and moods | closed | 2026-10-06: **two registers**, *useful* and *fun*; *"let Claude decide to create variations and natural"*. Default mood per class, Claude may choose another through the skill: design §4–§5. 2026-10-06: design validated (*"deal to both"*); go for milestones M1–M2 |
| D-0009 | Public / private boundary through a gitignored companion file | superseded | Raised 2026-10-06 when the repository was ruled public. 2026-10-06: superseded by D-0010 |
| D-0010 | `CLAUDE.md` is standalone and private (gitignored); tracked files carry no personal paths, private configuration or business context | closed | Lead's ruling 2026-10-06: *"make a CLAUDE.md independent … gitignore CLAUDE.md"*. 2026-10-06: history rewritten on the lead's instruction (*"force remove CLAUDE.md"*): no commit of `main` contains it (force-push, `c5c4917`) |
| D-0011 | No pre-commit hook for this repository | closed | Lead's ruling 2026-10-06: *"no (if yes, it would be only for this project)"* |
| D-0012 | Purge the orphaned bootstrap commit from GitHub by deleting and recreating `ovitrac/TalkToMe` | open | 2026-10-06: approved by the lead (*"1+2 OK"*). Deletion refused by the agent's safety policy (irreversible); awaits the lead's own `gh repo delete`, then recreation and push of the clean history |
| D-0013 | Every session has a gender: "he" or "she", never "it"; English voice and *his*/*her* follow it in both registers; improvised from the name, overridable | closed | Lead's rulings 2026-10-06: *"gender for both registers"*, *"I like the improvisation"* (no seeded lexicon), *"I prefer to interact with a his/her than with a it = cold object = dead"*. Design §5.1 |
| D-0014 | No male voice in French: `ff_siwis` speaks for every session | closed | Lead's ruling 2026-10-06: *"no male voice in French, ok"*, after the probe of five candidates (English male voices reading French 114–146 Hz; blends 163–177 Hz; `ff_siwis` −5 st 156 Hz) |
