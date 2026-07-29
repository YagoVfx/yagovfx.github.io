"""
Recruitee adapter.

Official, documented, public (no-auth) offers feed:
    GET https://{company}.recruitee.com/api/offers/
(also works on a custom domain: https://careers.company.com/api/offers/)

Docs: https://docs.recruitee.com/reference/offers
Single response, no pagination, no filtering support on this endpoint.
"""
import re
import logging
from urllib.parse import urlparse
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)


def build_recruitee_api_url(careers_url: str) -> str | None:
    """Works both for the standard {company}.recruitee.com subdomain and
    for a custom domain that has Recruitee's /api/offers path enabled."""
    if not careers_url:
        return None
    parsed = urlparse(careers_url if "://" in careers_url else f"https://{careers_url}")
    if not parsed.netloc:
        return None
    return f"https://{parsed.netloc}/api/offers/"


class RecruiteeAdapter(BaseAdapter):
    ats_type = "recruitee"

    def fetch_jobs(self) -> list[dict]:
        api_url = build_recruitee_api_url(self.careers_url)
        if not api_url:
            logger.error(f"[Recruitee] Cannot build API URL from {self.careers_url}")
            return []

        r = http_get(api_url)
        if not r:
            raise RuntimeError(f"No response from Recruitee API ({api_url})")
        try:
            data = r.json()
        except Exception as e:
            raise RuntimeError(f"Invalid JSON from Recruitee API ({api_url}): {e}")

        raw_jobs = data.get("offers", [])
        self.total_seen = len(raw_jobs)

        jobs = []
        for j in raw_jobs:
            title = j.get("title", "")
            description = j.get("description_plain", "") or j.get("description", "") or ""
            match = classify_job(title, description)
            if not match:
                continue

            locations = j.get("locations", [])
            loc = ", ".join(f"{l.get('city', '')} {l.get('country', '')}".strip() for l in locations if l).strip(", ")
            if not loc:
                loc = j.get("city", "") or ""
            remote_flag = "remote" if j.get("remote") else ""
            wt = detect_workplace(title, f"{loc} {remote_flag}", "")
            rs = detect_remote_scope(title, loc)

            slug = j.get("slug", "") or j.get("id", title)
            careers_page_url = j.get("careers_url", "") or ""
            jobs.append(self.normalize({
                "id": f"rc-{re.sub(r'[^a-z0-9]', '-', str(slug).lower())[-40:]}",
                "title": title,
                "url": careers_page_url,
                "location": loc,
                "workplaceType": wt,
                "remoteScope": rs,
                "matchType": match,
            }))
        return jobs
