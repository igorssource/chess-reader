"""Finished results kept for a while, so a phone that fell asleep or lost the
connection during the reading can still pick up the game it already paid for.

The page makes a random job id, sends it with the photos and, if the answer does
not arrive, asks GET /api/result/<job> until the result is there.
"""
from __future__ import annotations

import re

JOB_RE = re.compile(r"[A-Za-z0-9_-]{16,64}")
KEEP_SECONDS = 24 * 3600        # a result can be picked up for one day
RUNNING = 0                     # "status" while the reading is still going on


def valid_job(job: str | None) -> str | None:
    return job if job and JOB_RE.fullmatch(job) else None


def _key(job: str) -> str:
    return f"result:{job}"


def mark_running(kv, job: str):
    try:
        kv.set_json(_key(job), {"status": RUNNING}, KEEP_SECONDS)
    except Exception:           # keeping a copy must never break the reading itself
        pass


def save(kv, job: str, status: int, body: dict):
    try:
        kv.set_json(_key(job), {"status": status, "body": body}, KEEP_SECONDS)
    except Exception:
        pass


def load(kv, job: str):
    return kv.get_json(_key(job))
