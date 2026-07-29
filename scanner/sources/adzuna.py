"""
Adzuna aggregator source.

Two distinct uses of Adzuna in this scanner:

1. fetch_adzuna_jobs(): a broad keyword search ("VFX artist") across
   Adzuna's aggregated index, run once per scan across several countries.
   Every result is tagged "viaAggregator": true because clicking through
   always lands on an Adzuna interstitial page first (their
   affiliate-redirect business model, confirmed from their own public API
   docs — only `redirect_url` is exposed, never a direct source link).

2. find_signal_matches(): given the SAME broad result set from (1) and a
   list of companies we don't trust our own scrape of (needsReview), finds
   which of those companies have at least one current VFX-relevant
   listing indexed by Adzuna. Deliberately reuses the broad search results
   instead of issuing a new per-company query — an earlier version
   combined "{company name} VFX" into one query, which Adzuna treats as
   "all of these words must appear", making it far too strict for
   multi-word company names (it would almost never match, even when a
   real listing existed under different phrasing). Comparing against
   results we already fetched avoids that failure mode and costs zero
   extra API calls.

Both require ADZUNA_APP_ID / ADZUNA_APP_KEY as environment variables (set
as GitHub Actions secrets). If unset, both no-op / return empty results so
the rest of the scanner keeps working normally.
"""
import os
import logging
import difflib
import re
import requests
from ..filters import classify_job, detect_workplace, detect_remote_scope
from ..adapters.base import HEADERS, TIMEOUT
from ..company_category import classify_company_category

logger = logging.getLogger(__name__)

DEFAULT_COUNTRIES = ["gb", "us", "de", "fr", "nl", "ca", "es", "se"]
RESULTS_PER_PAGE = 20
MAX_PAGES_PER_COUNTRY = 2

# Corporate suffixes stripped before comparing two company names, so e.g.
# "CD Projekt Red S.A." and "CD Projekt RED" compare more fairly.
_SUFFIX_RE = re.compile(
    r'\b(inc|ltd|llc|gmbh|s\.?a\.?|s\.?r\.?l\.?|studio|studios|games?|entertainment|interactive|corp|corporation|co)\b\.?',
    re.IGNORECASE
)
_PUNCT_RE = re.compile(r'[^a-z0-9 ]+')


def _credentials():
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    return app_id, app_key


def _normalize_company_name(name: str) -> str:
    name = (name or "").lower()
    # Strip corporate suffixes BEFORE removing punctuation — patterns like
    # "S.A." or "Ltd." only match while the periods are still present.
    name = _SUFFIX_RE.sub(" ", name)
    name = _PUNCT_RE.sub(" ", name)
    return re.sub(r"\s+", " ", name).strip()


def company_names_match(name_a: str, name_b: str, threshold: float = 0.72) -> bool:
    """Fuzzy match tolerant of legal-name vs common-name differences
    ("CD Project" vs "CD Projekt Red S.A.", "EA" vs "Electronic Arts").
    Cheap substring check first, falls back to a similarity ratio
    (difflib, stdlib only — no new dependency) so near-misses in spelling
    still count.
    """
    a, b = _normalize_company_name(name_a), _normalize_company_name(name_b)
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= threshold


def fetch_adzuna_jobs(query: str = "VFX artist", countries: list[str] | None = None) -> tuple[list[dict], dict]:
    """Returns (normalized_jobs, status_dict)."""
    app_id, app_key = _credentials()
    if not app_id or not app_key:
        logger.info("[Adzuna] ADZUNA_APP_ID / ADZUNA_APP_KEY not set — skipping this source")
        return [], {"source": "Adzuna", "company": "(Adzuna — broad keyword search, not one company)", "status": "skipped", "reason": "no credentials configured"}

    countries = countries or DEFAULT_COUNTRIES
    jobs: list[dict] = []
    total_seen = 0
    seen_ids = set()

    for country in countries:
        for page in range(1, MAX_PAGES_PER_COUNTRY + 1):
            url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "what": query,
                "results_per_page": RESULTS_PER_PAGE,
                "content-type": "application/json",
            }
            try:
                r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                logger.warning(f"[Adzuna] Request failed for {country} page {page}: {e}")
                break

            results = data.get("results", [])
            if not results:
                break
            total_seen += len(results)

            for j in results:
                jid = j.get("id")
                if not jid or jid in seen_ids:
                    continue
                seen_ids.add(jid)

                title = j.get("title", "")
                description = j.get("description", "") or ""
                match = classify_job(title, description)
                if not match:
                    continue

                loc = (j.get("location") or {}).get("display_name", "")
                company = (j.get("company") or {}).get("display_name", "Unknown")
                wt = detect_workplace(title, loc, description[:200])
                rs = detect_remote_scope(title, loc)

                jobs.append({
                    "id": f"az-{jid}",
                    "company": company,
                    "title": title,
                    "url": j.get("redirect_url", ""),
                    "location": loc,
                    "workplaceType": wt,
                    "remoteScope": rs,
                    "ats": "adzuna",
                    "matchType": match,
                    "companyCategory": classify_company_category(company),
                    "viaAggregator": True,
                    "status": "active",
                })

            if len(results) < RESULTS_PER_PAGE:
                break

    return jobs, {
        "source": "Adzuna",
        "company": "(Adzuna — broad keyword search, not one company)",
        "status": "ok",
        "countriesQueried": len(countries),
        "totalPostingsSeen": total_seen,
        "jobsFound": len(jobs),
    }


def find_signal_matches(adzuna_jobs: list[dict], companies_to_check: list[dict]) -> tuple[dict, list[str]]:
    """Given the broad Adzuna result set and a list of companies we don't
    trust our own scrape of, returns (signal_by_company_name, matched_adzuna_job_ids):
    - signal_by_company_name: {company_name: True} for every company with
      at least one fuzzy-matching Adzuna result.
    - matched_adzuna_job_ids: ids of the specific Adzuna jobs that matched,
      so the caller can drop them from the broad list (we show the safer
      direct-link "signal" version for that company instead of the raw
      Adzuna listing).
    """
    signals = {}
    matched_ids = []
    for company in companies_to_check:
        name = company["name"]
        for job in adzuna_jobs:
            if company_names_match(name, job["company"]):
                signals[name] = True
                matched_ids.append(job["id"])
    return signals, matched_ids
