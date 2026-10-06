#!/bin/sh
# TalkToMe hook entry. Passes the event (stdin) to `talktome hook`; prints nothing and always exits 0,
# so a missing or broken installation can never block or alter a Claude Code session.
# Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
# License: MIT
for t in "$(command -v talktome 2>/dev/null)" "$HOME/.local/bin/talktome"; do
  if [ -n "$t" ] && [ -x "$t" ]; then
    "$t" hook >/dev/null 2>&1
    exit 0
  fi
done
exit 0
