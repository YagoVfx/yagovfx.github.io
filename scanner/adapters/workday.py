"""
Workday adapter.

Many large studios (Activision Blizzard, and often EA / Ubisoft / 2K-style
enterprise employers) run their real job data on Workday, even when they
also show a prettier front-end (Phenom People, custom React, etc).

Workday career sites look like:
    https://{tenant}.{wdHost}.myworkdayjobs.com/{site}
e.g.
    https://activision.wd1.myworkdayjobs.com/Blizzard_External_Careers
    https://activision.wd1.myworkdayjobs.com/External

The site itself calls an unauthenticated JSON API (the "CXS" endpoint) to
render its own listings:
    POST https://{tenant}.{wdHost}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs

No API key, no login — it's the same request the browser makes. We just
call it directly with `requests`, the same approach used for Greenhouse
and Lever.
"""
import re
import logging
import requests
from .base import BaseAdapter, HEADERS, TIMEOUT
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)

WORKDAY_URL_RE = re.compile(
    r'https?://([^./]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([^/?#]+)',
    re.IGNORECASE
)

PAGE_SIZE = 20
MAX_PAGES = 10  # safety cap: up to 200 postings per company per run


def parse_workday_url(url: str):
    """Return (tenant, wdHost, site) or None if the URL doesn't match."""
    m = WORKDAY_URL_RE.search(url or "")
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3)


class WorkdayAdapter(BaseAdapter):
    ats_type = "workday"

    def fetch_jobs(self) -> list[dict]:
        parsed = parse_workday_url(self.careers_url)
        if not parsed:
            logger.error(f"[Workday] Cannot parse tenant/site from {self.careers_url}")
            return []
        tenant, wd_host, site = parsed
        base_host = f"https://{tenant}.{wd_host}.myworkdayjobs.com"
        api_url = f"{base_host}/wday/cxs/{tenant}/{site}/jobs"

        jobs = []
        offset = 0
        total = None

        for _ in range(MAX_PAGES):
            payload = {"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": ""}
            try:
                r = requests.post(
                    api_url, json=payload,
                    headers={**HEADERS, "Content-Type": "application/json"},
                    timeout=TIMEOUT,
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                if offset == 0:
                    # Failed before getting anything at all — a real error,
                    # not "this company just has 0 postings".
                    raise RuntimeError(f"Workday request failed for {api_url}: {e}")
                logger.warning(f"[Workday] Request failed on a later page for {api_url}: {e} — returning partial results")
                break

            postings = data.get("jobPostings", [])
            if total is None:
                total = data.get("total", len(postings))
            if not postings:
                break
            self.total_seen += len(postings)

            for p in postings:
                title = p.get("title", "")
                match = classify_job(title, "")
                if not match:
                    continue
                loc = p.get("locationsText", "")
                path = p.get("externalPath", "")
                url = f"{base_host}/{site}{path}" if path else base_host
                wt = detect_workplace(title, loc, "")
                rs = detect_remote_scope(title, loc)
                job_id = p.get("bulletFields", [None])
                job_id = job_id[0] if job_id and job_id[0] else (path or title)
                jobs.append(self.normalize({
                    "id": f"wd-{re.sub(r'[^a-z0-9]', '-', str(job_id).lower())[-40:]}",
                    "title": title,
                    "url": url,
                    "location": loc,
                    "workplaceType": wt,
                    "remoteScope": rs,
                    "matchType": match,
                }))

            offset += PAGE_SIZE
            if total is not None and offset >= total:
                break

        return jobs
