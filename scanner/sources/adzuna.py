"""
Adzuna aggregator source.

Two distinct uses of Adzuna in this scanner:

1. fetch_adzuna_jobs(): a broad keyword search ("VFX artist") across
   Adzuna's aggregated index, run once per scan across several countries.
   Fills gaps for studios we can't reliably scrape directly. Every result
   is tagged "viaAggregator": true because clicking through always lands
   on an Adzuna interstitial page first (their affiliate-redirect business
   model — not something a different API call can bypass, confirmed from
   their own public API docs, which only expose `redirect_url`).

2. check_company_has_vfx_signal(): a targeted, per-company check used ONLY
   for companies whose direct adapter is flagged "needsReview" (i.e. we
   don't trust our own scrape of their site — usually a JS-rendered page
   we can't parse). Instead of adding Adzuna's own indirect job listing
   for that company, the scanner uses this as a yes/no "is there currently
   a VFX opening indexed for this company" signal, and if true, links
   straight to the COMPANY'S OWN careers URL (already known, direct, no
   interstitial, no click limits) rather than to anything on Adzuna. This
   trades exact job details (title/location of the specific posting) for
   a completely direct link — a deliberate tradeoff for the "at least get
   me to the right page, even if not the exact job" case.

Both require ADZUNA_APP_ID / ADZUNA_APP_KEY as environment variables (set
as GitHub Actions secrets). If unset, both functions no-op / return False
so the rest of the scanner keeps working normally.
"""
import os
import logging
import requests
from ..filters import classify_job, detect_workplace, detect_remote_scope
from ..adapters.base import HEADERS, TIMEOUT
from ..company_category import classify_company_category

logger = logging.getLogger(__name__)

DEFAULT_COUNTRIES = ["gb", "us", "de", "fr", "nl", "ca", "es", "se"]
RESULTS_PER_PAGE = 20
MAX_PAGES_PER_COUNTRY = 2

# For the targeted per-company signal check, searching a handful of the
# most likely countries is enough to answer "yes/no" without spending the
# whole daily quota on companies that may only post in one region anyway.
SIGNAL_CHECK_COUNTRIES = ["gb", "us", "de"]


def _credentials():
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    return app_id, app_key


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


def check_company_has_vfx_signal(company_name: str, countries: list[str] | None = None) -> bool:
    """Targeted check: does Adzuna currently have ANY listing that both (a)
    mentions this company and (b) has a VFX-relevant title? Used only as a
    yes/no signal for companies we already don't trust our own scrape of —
    see module docstring. Returns False (not an error) if credentials are
    missing, on any request failure, or if nothing matches — callers
    should treat False as "no confirmed signal", not proof there's nothing.
    """
    app_id, app_key = _credentials()
    if not app_id or not app_key or not company_name:
        return False

    countries = countries or SIGNAL_CHECK_COUNTRIES
    name_lower = company_name.strip().lower()

    for country in countries:
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "what": f"{company_name} VFX",
            "results_per_page": 20,
            "content-type": "application/json",
        }
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.info(f"[Adzuna signal check] Request failed for '{company_name}' in {country}: {e}")
            continue

        for j in data.get("results", []):
            result_company = ((j.get("company") or {}).get("display_name", "") or "").strip().lower()
            if not result_company:
                continue
            # Loose substring match either direction: aggregator listings
            # often have slightly different company name formatting
            # ("EA" vs "Electronic Arts", trailing "Ltd"/"Inc", etc.).
            if name_lower not in result_company and result_company not in name_lower:
                continue
            if classify_job(j.get("title", ""), j.get("description", "") or ""):
                return True

    return False
