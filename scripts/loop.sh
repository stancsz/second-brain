#!/bin/bash
# Mochu outer loop — budget-capped fire-and-forget harness with separated gating.
# The builder instance NEVER gates its own merge: the gate runs as a fresh process
# after every iteration, and the loop HALTS on gate failure (never compound on corrupt state).
#
# Usage:  MOCHU_CMD='claude -p "Use the mochu skill: run one iteration on this repo"' \
#         MAX_ITERS=50 MAX_SECONDS=7200 bash scripts/loop.sh [repo_root]
# Vars:   MOCHU_CMD     (required) command that performs ONE mochu iteration
#         GATE_CMD      (default: python3 scripts/ship_gate.py) — run in a fresh process per iteration
#         MAX_ITERS     (default 50)  hard cap on iterations — set ridiculously high; RELEASE-READY exits early anyway
#         MAX_SECONDS   (default 7200) wallclock cap PER iteration (2hr); real work takes time
# Routing tip: alternate tiers — e.g. MOCHU_CMD pointing at your strongest model on
# judgment iterations and Sonnet on build-heavy ones; Haiku is fine for recon iterations.
set -u
ROOT="${1:-.}"; cd "$ROOT" || exit 2
: "${MOCHU_CMD:?set MOCHU_CMD to the command that runs one mochu iteration}"
GATE_CMD="${GATE_CMD:-python3 scripts/ship_gate.py}"
MAX_ITERS="${MAX_ITERS:-50}"; MAX_SECONDS="${MAX_SECONDS:-7200}"
LOG=".mochu/loop.log"; mkdir -p .mochu

for i in $(seq 1 "$MAX_ITERS"); do
  echo "=== iter $i $(date '+%F %T')" | tee -a "$LOG"
  timeout "$MAX_SECONDS" bash -c "$MOCHU_CMD" >> "$LOG" 2>&1
  rc=$?
  [ "$rc" -eq 124 ] && echo "iter $i TIMEOUT after ${MAX_SECONDS}s — parked by harness" | tee -a "$LOG"
  if ! bash -c "$GATE_CMD" >> "$LOG" 2>&1; then
    echo "iter $i GATE FAIL — halting loop; inspect $LOG and .mochu/ before resuming" | tee -a "$LOG"
    exit 1
  fi
  tail -n 1 .mochu/ledger.md 2>/dev/null | tee -a "$LOG"
  grep -q "RELEASE-READY" .mochu/ledger.md 2>/dev/null && { echo "RELEASE-READY — loop complete" | tee -a "$LOG"; exit 0; }
done
echo "MAX_ITERS=$MAX_ITERS reached — loop complete" | tee -a "$LOG"