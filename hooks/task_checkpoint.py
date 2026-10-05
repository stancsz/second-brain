#!/usr/bin/env python3
"""Codex Stop/SubagentStop hook that requests a Second Brain task checkpoint.

The hook does not write to the brain itself: it cannot reliably infer semantic
task progress from a transcript. It gives the agent one continuation turn to
record a concise checkpoint, then fails open to avoid trapping the conversation.
"""

from __future__ import annotations

import json
import sys


MARKERS = (
    "SECOND_BRAIN_CHECKPOINT: saved",
    "SECOND_BRAIN_CHECKPOINT: skip",
    "SECOND_BRAIN_CHECKPOINT: unavailable",
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0

    if not isinstance(payload, dict):
        return 0

    message = payload.get("last_assistant_message") or ""
    if any(marker in message for marker in MARKERS):
        return 0

    # A continuation can trigger this hook again. On that second pass, allow
    # the agent to finish even if it could not reach the brain.
    if payload.get("stop_hook_active"):
        return 0

    response = {
        "decision": "block",
        "reason": (
            "Before finishing, follow AGENTS.md and checkpoint substantive "
            "project work in Second Brain: task name, estimated completion "
            "percentage, completed work, remaining work/blockers, and "
            "verification. Search and update the same Work concept when one "
            "clearly matches; otherwise add one. Do not save raw transcripts. "
            "For ordinary Q&A with no meaningful project work, make no entry. "
            "End with exactly one marker: SECOND_BRAIN_CHECKPOINT: saved, "
            "skip, or unavailable."
        ),
    }
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # A checkpoint hook must never make an otherwise usable session fail.
        raise SystemExit(0)
