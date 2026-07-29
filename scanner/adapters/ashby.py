"""
Ashby adapter.

Official, documented, public, no-auth Job Postings API:
    GET https://api.ashbyhq.com/posting-api/job-board/{jobBoardName}?includeCompensation=true

Docs: https://developers.ashbyhq.com/docs (Ashby Job Postings API).
Single response, no pagination. Returns workplaceType per job (recent
addition), which we use directly instead of guessing from free text.
"""
import re
import logging
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)


def extract_ashby_board(url: str) -> str | None:
    m = re.search(r'(?:jobs\.ashbyhq\.com|ashbyhq\.com/posting-api/job-board)/([a-zA-Z0-9_-]+)', url or "")
    return m.group(1) if m else None


class AshbyAdapter(BaseAdapter):
    ats_type = "ashby"

    def fetch_jobs(self) -> list[dict]:
        board = extract_ashby_board(self.careers_url)
        if not board:
            logger.error(f"[Ashby] Cannot parse job board name from {self.careers_url}")
            return []

        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true"
        r = http_get(api_url)
        if not r:
            raise RuntimeError(f"No response from Ashby API for board '{board}' ({api_url})")
        try:
            data = r.json()
        except Exception as e:
            raise RuntimeError(f"Invalid JSON from Ashby API for board '{board}': {e}")

        raw_jobs = data.get("jobs", [])
        self.total_seen = len(raw_jobs)

        jobs = []
        for j in raw_jobs:
            title = j.get("title", "")
            description = j.get("descriptionPlain", "") or j.get("descriptionHtml", "") or ""
            match = classify_job(title, description)
            if not match:
                continue

            loc = j.get("location", "") or j.get("addressLocality", "") or ""
            ashby_wt = (j.get("workplaceType") or "").lower()  # 'remote' | 'onsite' | 'hybrid' (new field)
            wt = ashby_wt if ashby_wt in ("remote", "onsite", "hybrid") else detect_workplace(title, loc, "")
            rs = detect_remote_scope(title, loc)

            job_id = j.get("id") or j.get("jobId") or title
            jobs.append(self.normalize({
                "id": f"ab-{re.sub(r'[^a-z0-9]', '-', str(job_id).lower())[-40:]}",
                "title": title,
                "url": j.get("jobUrl", "") or j.get("applyUrl", ""),
                "location": loc,
                "workplaceType": wt,
                "remoteScope": rs,
                "matchType": match,
            }))
        return jobs
