import re
import logging
import requests
from .base import BaseAdapter, HEADERS, TIMEOUT
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)

PAGE_SIZE = 100
MAX_PAGES = 5


def extract_smartrecruiters_company(url: str) -> str | None:
    # api.smartrecruiters.com/v1/companies/{id}/postings — the raw API URL
    # form, checked FIRST since it's more specific (otherwise the looser
    # pattern below would incorrectly grab "v1" as if it were the company
    # identifier).
    m = re.search(r'api\.smartrecruiters\.com/v1/companies/([a-zA-Z0-9_-]+)', url or "", re.IGNORECASE)
    if m:
        return m.group(1)
    # jobs.smartrecruiters.com/{id} or careers.smartrecruiters.com/{id} —
    # the public-facing career-site URL form.
    m = re.search(r'smartrecruiters\.com/(?:companies/)?([a-zA-Z0-9_-]+)', url or "", re.IGNORECASE)
    return m.group(1) if m else None


class SmartRecruitersAdapter(BaseAdapter):
    ats_type = "smartrecruiters"
    uses_reliable_api = True

    def fetch_jobs(self) -> list[dict]:
        company = extract_smartrecruiters_company(self.careers_url)
        if not company:
            logger.error(f"[SmartRecruiters] Cannot parse company identifier from {self.careers_url}")
            return []

        jobs = []
        offset = 0
        total_found = None

        for _ in range(MAX_PAGES):
            api_url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings"
            try:
                r = requests.get(api_url, params={"limit": PAGE_SIZE, "offset": offset}, headers=HEADERS, timeout=TIMEOUT)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                if offset == 0:
                    raise RuntimeError(f"SmartRecruiters request failed for '{company}' ({api_url}): {e}")
                logger.warning(f"[SmartRecruiters] Later page failed for '{company}': {e} — returning partial results")
                break

            content = data.get("content", [])
            if total_found is None:
                total_found = data.get("totalFound", len(content))
            if not content:
                break
            self.total_seen += len(content)

            for j in content:
                title = j.get("name", "")
                match = classify_job(title, "")
                if not match:
                    continue
                loc_obj = j.get("location", {}) or {}
                loc = ", ".join(p for p in (loc_obj.get("city"), loc_obj.get("region"), loc_obj.get("country")) if p)
                remote_flag = "remote" if loc_obj.get("remote") else ""
                wt = detect_workplace(title, f"{loc} {remote_flag}", "")
                rs = detect_remote_scope(title, loc)
                posting_id = j.get("id", title)
                ref_id = j.get("refNumber", "")
                jobs.append(self.normalize({
                    "id": f"sr-{re.sub(r'[^a-z0-9]', '-', str(posting_id).lower())[-40:]}",
                    "title": title,
                    "url": j.get("ref", "") or f"https://jobs.smartrecruiters.com/{company}/{ref_id or posting_id}",
                    "location": loc,
                    "workplaceType": wt,
                    "remoteScope": rs,
                    "matchType": match,
                }))

            offset += PAGE_SIZE
            if total_found is not None and offset >= total_found:
                break

        return jobs
