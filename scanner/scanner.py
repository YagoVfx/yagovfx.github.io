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
from scanner.sources.adzuna import fetch_adzuna_jobs, check_company_has_vfx_signal

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("scanner")

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

COMPANIES_FILE = DATA_DIR / "companies.json"
JOBS_FILE = DATA_DIR / "jobs.json"
STATUS_FILE = DATA_DIR / "scanner-status.json"

# Priority order, cheapest/most-reliable first: official API > AJAX/JSON
# endpoint > plain HTML > aggregator as a last resort. Adzuna's
# "last resort" behavior is enforced in two ways below, not just by this
# lookup table: (1) it only runs after every company adapter, and its
# results are dropped whenever a direct adapter already found the same
# job; (2) for companies we don't trust our own scrape of, we use Adzuna
# only as a yes/no signal and link to the company's OWN page instead of
# to Adzuna's.
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
    """Adzuna is a last resort, not a competing duplicate: if a company
    adapter already found this exact job directly (same company + same
    title), keep the direct link and drop the Adzuna copy.
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


def build_signal_job(company: dict, now: str) -> dict:
    """A 'we think there's something here, go look' entry — used when a
    company's direct scrape is untrusted (needsReview) but Adzuna confirms
    a current VFX-relevant listing exists for them. Deliberately vague on
    title/location (we don't have reliable access to those), but the URL
    goes straight to the company's OWN careers page — never to Adzuna.
    """
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
            # A trustworthy API returning 0 postings means "genuinely zero
            # open positions right now" — not suspicious. Only an
            # HTML-scraping heuristic (uses_reliable_api=False) reporting
            # 0 candidates is ambiguous enough to flag for review (could be
            # a JS-rendered page, a block, or our own link-matching missing
            # them).
            needs_review = (total_seen == 0) and not uses_reliable_api
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
            # A hard error also means we don't trust this company's data —
            # worth checking for an Adzuna signal too, same as needsReview.
            needs_review_companies.append(company)

    # Targeted Adzuna signal check — ONLY for companies we don't trust our
    # own scrape of. This is the user-proposed approach: instead of adding
    # Adzuna's own (indirect, interstitial) listing, confirm a signal and
    # link straight to the company's own careers page.
    now = now_iso()
    signal_jobs_added = 0
    for company in needs_review_companies:
        try:
            if check_company_has_vfx_signal(company["name"]):
                job = build_signal_job(company, now)
                preserve_first_seen(existing, job)
                new_jobs[job["id"]] = job
                signal_jobs_added += 1
        except Exception as e:
            logger.info(f"[Adzuna signal check] Skipped for {company['name']}: {e}")

    # Adzuna broad keyword search: last resort, fills remaining gaps. Runs
    # on top of (not instead of) everything above, and never duplicates a
    # job a direct adapter already found.
    adzuna_jobs, adzuna_status = fetch_adzuna_jobs()
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
