"""
Normalization helpers used when merging a fresh scan against the
previously stored jobs.json: stable id generation and firstSeen /
lastSeen bookkeeping.

Workplace-type and remote-scope detection live in scanner/filters.py
(they're about classifying a *job*, not about merging *runs*), and are
re-exported here for convenience so callers only need one import when
they want "everything normalization-related".
"""
import re
from datetime import datetime, timezone

from .filters import detect_workplace, detect_remote_scope  # re-exported

__all__ = [
    "detect_workplace",
    "detect_remote_scope",
    "generate_job_id",
    "now_iso",
    "preserve_first_seen",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_job_id(prefix: str, unique_str: str) -> str:
    """Build a short, stable, filesystem/JSON-safe id from a prefix
    (e.g. 'gh', 'lv', 'tt', 'ch') and any unique string (usually the
    job URL). Same input always produces the same id, which is what
    lets us match a job across scanner runs without a database.
    """
    safe = re.sub(r"[^a-z0-9]+", "-", unique_str.lower()).strip("-")
    return f"{prefix}-{safe[-40:]}" if safe else f"{prefix}-{uid_fallback(unique_str)}"


def uid_fallback(seed: str) -> str:
    # Extremely unlikely path (empty/garbage input); keeps generate_job_id total.
    return str(abs(hash(seed)))[:10]


def preserve_first_seen(existing_jobs: dict, job: dict, now: str | None = None) -> dict:
    """Given the map of previously known jobs (id -> job dict) and a
    freshly scraped job dict, set firstSeen/lastSeen correctly:
    - if the job existed before, keep its original firstSeen
    - otherwise this is the first time we've seen it, so firstSeen = now
    - lastSeen is always refreshed to now
    Returns the same job dict, mutated in place, for convenience.
    """
    now = now or now_iso()
    jid = job["id"]
    if jid in existing_jobs and existing_jobs[jid].get("firstSeen"):
        job["firstSeen"] = existing_jobs[jid]["firstSeen"]
    else:
        job["firstSeen"] = job.get("firstSeen") or now
    job["lastSeen"] = now
    return job
