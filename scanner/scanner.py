import json, logging, re, sys
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
from scanner.company_category import classify_company_category
from scanner.sources.adzuna import fetch_adzuna_jobs, find_signal_matches

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("scanner")

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

COMPANIES_FILE = DATA_DIR / "companies.json"
JOBS_FILE = DATA_DIR / "jobs.json"
STATUS_FILE = DATA_DIR / "scanner-status.json"

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


def build_signal_job(company: dict, now: str) -> dict:
    name = company["name"]
    return {
        "id": f"sig-{re.sub(r'[^a-z0-9]', '-', name.lower())}",
        "company": name,
        "title": "Posible oferta VFX detectada — ver listado completo",
        "url": company["careersUrl"],
        "location": "",
        "workplaceType": "unknown",
        "remoteScope": "unknown",
        "ats": "adzuna-signal",
        "matchType": "possibleMatch",
        "companyCategory": classify_company_category(name, company.get("category")),
        "viaAggregator": False,
        "signalOnly": True,
        "firstSeen": now,
        "lastSeen": now,
        "status": "active",
    }


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
    needs_review_companies = []

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
            uses_reliable_api = getattr(adapter, "uses_reliable_api", True)
            # Broadened on purpose: it's not just "0 candidates seen at all"
            # that's suspicious for an HTML-scraping heuristic — "we saw
            # postings but matched none" is equally untrustworthy for those
            # adapters (proven in practice: e.g. EA's page had real VFX
            # roles while our scraper counted 40 unrelated candidates and
            # matched 0). A real structured API (Greenhouse, Ashby...)
            # reporting 0 matches IS trustworthy — its title data isn't a
            # heuristic guess, so that case stays un-flagged.
            needs_review = (len(found) == 0) and not uses_reliable_api
            if needs_review:
                needs_review_companies.append(company)
            statuses.append({
                "company": company["name"],
                "status": "ok",
                "jobsFound": len(found),
                "totalPostingsSeen": total_seen,
                "needsReview": needs_review,
                "lastAttempt": now_iso(),
            })
            succeeded += 1
        except Exception as e:
            logger.error(f"Error scanning {company['name']}: {e}")
            statuses.append({"company": company["name"], "status": "error", "error": str(e), "lastAttempt": now_iso()})
            failed += 1
            needs_review_companies.append(company)

    # Adzuna broad keyword search — fetched ONCE, used for two purposes:
    # (1) fill remaining gaps directly (last resort, tagged viaAggregator),
    # (2) as a reusable dataset to detect a "signal" for companies we
    # don't trust our own scrape of (see find_signal_matches). Doing (2)
    # against the SAME already-fetched results (rather than a new,
    # over-restrictive per-company query) is what actually makes the
    # signal system work reliably.
    adzuna_jobs, adzuna_status = fetch_adzuna_jobs()

    signals, matched_adzuna_ids = find_signal_matches(adzuna_jobs, needs_review_companies)
    matched_ids_set = set(matched_adzuna_ids)
    # Don't show the raw (indirect, interstitial) Adzuna listing for a
    # company we're about to give a direct-link "signal" entry to instead.
    adzuna_jobs = [j for j in adzuna_jobs if j["id"] not in matched_ids_set]

    now = now_iso()
    signal_jobs_added = 0
    for company in needs_review_companies:
        if signals.get(company["name"]):
            job = build_signal_job(company, now)
            preserve_first_seen(existing, job)
            new_jobs[job["id"]] = job
            signal_jobs_added += 1

    adzuna_jobs = dedupe_adzuna_against_direct_matches(adzuna_jobs, new_jobs)
    adzuna_status["jobsFound"] = len(adzuna_jobs)
    adzuna_status["signalOnlyJobsAdded"] = signal_jobs_added
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

    logger.info(f"Done. {len(active_jobs)} active VFX jobs from {succeeded}/{len(companies)} studios. {signal_jobs_added} signal-only job(s) added.")


if __name__ == "__main__":
    run()
