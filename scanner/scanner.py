import json, logging, re, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.adapters.greenhouse import GreenhouseAdapter
from scanner.adapters.lever import LeverAdapter
from scanner.adapters.teamtailor import TeamtailorAdapter
from scanner.adapters.custom_html import CustomHtmlAdapter
from scanner.adapters.workday import WorkdayAdapter
from scanner.adapters.workable import WorkableAdapter
from scanner.adapters.ashby import AshbyAdapter
from scanner.adapters.smartrecruiters import SmartRecruitersAdapter
from scanner.adapters.recruitee import RecruiteeAdapter
from scanner.adapters.personio import PersonioAdapter
from scanner.companies import detect_ats, dedupe_companies
from scanner.normalizer import preserve_first_seen, now_iso
from scanner.sources.adzuna import fetch_adzuna_jobs

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("scanner")

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

COMPANIES_FILE = DATA_DIR / "companies.json"
JOBS_FILE = DATA_DIR / "jobs.json"
STATUS_FILE = DATA_DIR / "scanner-status.json"

# Priority order, cheapest/most-reliable first (per the project's own
# guiding principle: official API > AJAX/JSON endpoint > plain HTML >
# aggregator as a last resort). This dict is just the lookup table used
# below — the actual "last resort" behavior for Adzuna is enforced by
# running it after every company adapter and de-duplicating against
# whatever those already found (see dedupe_against_direct_matches below),
# not by this ordering alone.
ATS_MAP = {
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "ashby": AshbyAdapter,
    "smartrecruiters": SmartRecruitersAdapter,
    "recruitee": RecruiteeAdapter,
    "personio": PersonioAdapter,
    "teamtailor": TeamtailorAdapter,
    "workday": WorkdayAdapter,
    "workable": WorkableAdapter,
    "custom": CustomHtmlAdapter,
}


def load_existing_jobs() -> dict[str, dict]:
    if not JOBS_FILE.exists() or JOBS_FILE.stat().st_size == 0:
        return {}
    try:
        with open(JOBS_FILE) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        logger.warning(f"{JOBS_FILE} exists but is not valid JSON — starting fresh")
        return {}
    return {j["id"]: j for j in data.get("jobs", [])}


def _normalize_for_dedup(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def dedupe_adzuna_against_direct_matches(adzuna_jobs: list[dict], direct_jobs: dict) -> list[dict]:
    """Adzuna is meant to be a last resort, not a competing duplicate: if a
    company adapter already found this exact job directly (same company +
    same title), keep the direct link (no interstitial, no click limits)
    and drop the Adzuna copy instead of showing both.
    """
    direct_keys = {
        (_normalize_for_dedup(j["company"]), _normalize_for_dedup(j["title"]))
        for j in direct_jobs.values()
        if not j.get("viaAggregator")
    }
    kept = []
    skipped = 0
    for job in adzuna_jobs:
        key = (_normalize_for_dedup(job["company"]), _normalize_for_dedup(job["title"]))
        if key in direct_keys:
            skipped += 1
            continue
        kept.append(job)
    if skipped:
        logger.info(f"[Adzuna] Skipped {skipped} job(s) already found via a direct company adapter")
    return kept


def run():
    if not COMPANIES_FILE.exists():
        logger.error(f"companies.json not found at {COMPANIES_FILE}")
        sys.exit(1)

    with open(COMPANIES_FILE) as f:
        companies = json.load(f)
    companies = dedupe_companies(companies)

    existing = load_existing_jobs()
    new_jobs: dict[str, dict] = {}
    statuses = []
    succeeded = failed = 0

    for company in companies:
        ats = company.get("type") or detect_ats(company["careersUrl"])
        cls = ATS_MAP.get(ats, CustomHtmlAdapter)
        logger.info(f"Scanning {company['name']} via {ats}…")
        try:
            adapter = cls(company)
            found = adapter.fetch_jobs()
            for job in found:
                preserve_first_seen(existing, job)
                new_jobs[job["id"]] = job
            total_seen = getattr(adapter, "total_seen", None)
            statuses.append({
                "company": company["name"],
                "status": "ok",
                "jobsFound": len(found),
                "totalPostingsSeen": total_seen,
                # ok + 0 postings seen at all (not just 0 VFX matches) is
                # suspicious: probably a JS-rendered page, a block, or a
                # parser that no longer matches this site's HTML — flag it
                # instead of silently reporting a clean "ok".
                "needsReview": total_seen == 0,
                "lastAttempt": now_iso(),
            })
            succeeded += 1
        except Exception as e:
            logger.error(f"Error scanning {company['name']}: {e}")
            statuses.append({"company": company["name"], "status": "error", "error": str(e), "lastAttempt": now_iso()})
            failed += 1

    # Adzuna: last resort. Runs on top of (not instead of) the per-company
    # adapters above, and only ever fills gaps — any job it finds that a
    # direct adapter already found gets dropped in favor of the direct
    # link (no interstitial, no click limits). Optional — silently skipped
    # if no API credentials are set.
    adzuna_jobs, adzuna_status = fetch_adzuna_jobs()
    adzuna_jobs = dedupe_adzuna_against_direct_matches(adzuna_jobs, new_jobs)
    adzuna_status["jobsFound"] = len(adzuna_jobs)
    for job in adzuna_jobs:
        preserve_first_seen(existing, job)
        new_jobs[job["id"]] = job
    statuses.append(adzuna_status)

    for jid, job in existing.items():
        if jid not in new_jobs:
            job["status"] = "closed"
            job["lastSeen"] = now_iso()
            new_jobs[jid] = job

    active_jobs = [j for j in new_jobs.values() if j["status"] == "active"]

    output = {
        "lastUpdated": now_iso(),
        "companiesScanned": len(companies),
        "companiesSucceeded": succeeded,
        "companiesFailed": failed,
        "totalVfxJobs": len(active_jobs),
        "jobs": list(new_jobs.values()),
    }

    with open(JOBS_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    with open(STATUS_FILE, "w") as f:
        json.dump(statuses, f, indent=2, ensure_ascii=False)

    logger.info(f"Done. {len(active_jobs)} active VFX jobs from {succeeded}/{len(companies)} studios.")


if __name__ == "__main__":
    run()
