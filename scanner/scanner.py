
import json, logging, re, sys
from datetime import datetime, timezone
from pathlib import Path

# Make sure scanner package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.adapters.greenhouse import GreenhouseAdapter
from scanner.adapters.lever import LeverAdapter
from scanner.adapters.teamtailor import TeamtailorAdapter
from scanner.adapters.custom_html import CustomHtmlAdapter
from scanner.companies import detect_ats, dedupe_companies
from scanner.normalizer import preserve_first_seen, now_iso

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
    "teamtailor": TeamtailorAdapter,
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





def run():
    if not COMPANIES_FILE.exists():
        logger.error(f"companies.json not found at {COMPANIES_FILE}")
        sys.exit(1)

    with open(COMPANIES_FILE) as f:
        companies = json.load(f)
    companies = dedupe_companies(companies)   # <-- añadir esta línea

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
            statuses.append({"company": company["name"], "status": "ok", "jobsFound": len(found), "lastAttempt": now_iso()})
            succeeded += 1
        except Exception as e:
            logger.error(f"Error scanning {company['name']}: {e}")
            statuses.append({"company": company["name"], "status": "error", "error": str(e), "lastAttempt": now_iso()})
            failed += 1

    # Mark jobs not seen this run as closed (keep for 7 days)
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
