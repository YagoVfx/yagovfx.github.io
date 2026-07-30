"""
Automatic ATS discovery.

The core problem this solves: Adzuna's broad keyword search surfaces
plenty of real studios we've never configured in companies.json — but its
API only gives us `redirect_url` (through Adzuna's own interstitial page),
never a direct link. Manually researching each new studio's real ATS
(as done for Asobo Studio, Saber Interactive Spain, Gram Games, Shiro
Games) works, but doesn't scale to "every studio Adzuna happens to find".

Instead: many companies Adzuna indexes actually SOURCE their listing from
Greenhouse, Lever, or Ashby in the first place (Adzuna scraped it from
there) — these three all expose free, public, unauthenticated JSON APIs
keyed by a "board slug" that is very often just the company's name,
slugified. So for any company name we don't already have configured, we
can try a handful of plausible slug variants against these three APIs
directly. This is safe (not a guess at an arbitrary domain — we're
probing a known, structured, self-verifying namespace: if the slug is
wrong, the API just returns 404/empty, so there's no risk of linking
somewhere wrong or misleading) and needs zero manual research.

Results are cached (both hits AND misses) in data/ats-discovery-cache.json
so repeat scans don't re-probe the same company name over and over —
misses are allowed to be retried after a while (a studio might set up a
Greenhouse board later), hits are kept indefinitely (companies rarely
change ATS).
"""
import re
import json
import logging
import time
from pathlib import Path
import requests
from .adapters.base import HEADERS, TIMEOUT

logger = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).parent.parent / "data" / "ats-discovery-cache.json"
MISS_RETRY_SECONDS = 14 * 24 * 3600  # re-try a known miss after ~2 weeks
MAX_SLUG_CANDIDATES = 4


def _load_cache() -> dict:
    if not CACHE_FILE.exists() or CACHE_FILE.stat().st_size == 0:
        return {}
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def _save_cache(cache: dict):
    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _slugify_candidates(company_name: str) -> list[str]:
    """A handful of plausible board-slug variants for a company name.
    Ordered from most to least likely, capped at MAX_SLUG_CANDIDATES."""
    name = (company_name or "").lower().strip()
    name = re.sub(r"[^a-z0-9 ]+", "", name)
    words = name.split()
    if not words:
        return []

    candidates = []
    joined_hyphen = "-".join(words)
    joined_plain = "".join(words)
    candidates.append(joined_plain)
    candidates.append(joined_hyphen)

    # Studios are frequently boarded as "{name}games" / "{name}-games" even
    # when their public-facing name doesn't include the word "Games".
    if "games" not in words:
        candidates.append(joined_plain + "games")

    # First word alone, for cases like "Gram Games" -> "gram" (common when
    # the board predates a later company rename, or uses a short handle).
    if len(words) > 1:
        candidates.append(words[0])

    # De-dupe while preserving order, cap length.
    seen = set()
    out = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out[:MAX_SLUG_CANDIDATES]


def _try_greenhouse(slug: str):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        data = r.json()
        jobs = data.get("jobs", [])
        if not jobs:
            return None
        return {"ats": "greenhouse", "careersUrl": f"https://job-boards.greenhouse.io/{slug}", "sample_count": len(jobs)}
    except Exception:
        return None


def _try_lever(slug: str):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        data = r.json()
        if not isinstance(data, list) or not data:
            return None
        return {"ats": "lever", "careersUrl": f"https://jobs.lever.co/{slug}", "sample_count": len(data)}
    except Exception:
        return None


def _try_ashby(slug: str):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=false"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        data = r.json()
        jobs = data.get("jobs", [])
        if not jobs:
            return None
        return {"ats": "ashby", "careersUrl": f"https://jobs.ashbyhq.com/{slug}", "sample_count": len(jobs)}
    except Exception:
        return None


_PROBERS = [_try_greenhouse, _try_lever, _try_ashby]


def discover_direct_source(company_name: str, cache: dict | None = None) -> dict | None:
    """Try to find a real Greenhouse/Lever/Ashby board for this company
    name, using cache to avoid re-probing. Returns a dict like
    {"ats": "greenhouse", "careersUrl": "..."} on success, or None.
    `cache` is mutated in place if provided (caller is responsible for
    persisting it with _save_cache / save_discovery_cache).
    """
    if cache is None:
        cache = {}
    key = (company_name or "").strip().lower()
    if not key:
        return None

    cached = cache.get(key)
    now = time.time()
    if cached:
        if cached.get("found"):
            return {"ats": cached["ats"], "careersUrl": cached["careersUrl"]}
        if now - cached.get("checkedAt", 0) < MISS_RETRY_SECONDS:
            return None  # recent miss, don't re-probe yet

    for slug in _slugify_candidates(company_name):
        for prober in _PROBERS:
            result = prober(slug)
            if result:
                cache[key] = {"found": True, "ats": result["ats"], "careersUrl": result["careersUrl"], "checkedAt": now}
                logger.info(f"[AutoDiscover] Found {result['ats']} board for '{company_name}' -> {result['careersUrl']}")
                return {"ats": result["ats"], "careersUrl": result["careersUrl"]}

    cache[key] = {"found": False, "checkedAt": now}
    return None


def load_discovery_cache() -> dict:
    return _load_cache()


def save_discovery_cache(cache: dict):
    _save_cache(cache)
