"""
Adzuna aggregator source.

Unlike the per-company adapters (Greenhouse, Lever, Workday...), this isn't
tied to one employer's careers page — it's a keyword search across
Adzuna's aggregated job index, which pulls from thousands of sources
(including many studios we can't reliably scrape directly, like EA,
Epic, Ubisoft — their JS-heavy career sites). It's a free public API:
sign up at https://developer.adzuna.com/ for an app_id + app_key.

No key hardcoded here — read from environment variables, set as GitHub
Actions secrets (see .github/workflows/vfx-jobs-scanner.yml):
    ADZUNA_APP_ID
    ADZUNA_APP_KEY

If those aren't set, fetch_adzuna_jobs() returns an empty list and logs a
notice — the rest of the scanner keeps working normally (this source is
optional, additive, never required).
"""
import os
import logging
import requests
from ..filters import classify_job, detect_workplace, detect_remote_scope
from ..adapters.base import HEADERS, TIMEOUT

logger = logging.getLogger(__name__)

# Adzuna is per-country, no single "worldwide" endpoint. This list covers
# where game studios most commonly post in English/major EU markets — add
# more 2-letter country codes here if you want broader coverage (each one
# is an extra set of requests though, so keep it reasonable).
DEFAULT_COUNTRIES = ["gb", "us", "de", "fr", "nl", "ca", "es", "se"]
RESULTS_PER_PAGE = 20
MAX_PAGES_PER_COUNTRY = 2  # keep it polite — this runs on every scan


def fetch_adzuna_jobs(query: str = "VFX artist", countries: list[str] | None = None) -> tuple[list[dict], dict]:
    """Returns (normalized_jobs, status_dict)."""
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        logger.info("[Adzuna] ADZUNA_APP_ID / ADZUNA_APP_KEY not set — skipping this source")
        return [], {"source": "Adzuna", "status": "skipped", "reason": "no credentials configured"}

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
                    "status": "active",
                })

            if len(results) < RESULTS_PER_PAGE:
                break  # last page for this country

    return jobs, {
        "source": "Adzuna",
        "status": "ok",
        "countriesQueried": len(countries),
        "totalPostingsSeen": total_seen,
        "jobsFound": len(jobs),
    }
