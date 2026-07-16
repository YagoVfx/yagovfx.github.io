"""
Workable adapter.

Workable exposes an unauthenticated "widget" JSON endpoint that powers its
own embeddable career-site widgets — the same one many companies embed on
their own custom domain (e.g. a Gatsby/React site that fetches this on the
client side, which is exactly why a plain HTML scraper sees nothing there).

    GET https://apply.workable.com/api/v1/widget/accounts/{account}?details=true

No API key, no login. Career pages look like:
    https://apply.workable.com/{account}/
    https://{account}.workable.com/          (legacy subdomain form)

If a company's careers page is on their OWN domain with Workable embedded
via JS (like https://lighthousegames.com/careers/), we can't derive the
Workable account slug from that URL alone — someone has to find it once
(e.g. via browser devtools Network tab, filter "workable") and then use
the direct https://apply.workable.com/{account} URL in companies.json
instead of the custom-domain one.
"""
import re
import logging
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)

WORKABLE_URL_RE = re.compile(
    r'https?://(?:apply\.workable\.com/|([a-z0-9-]+)\.workable\.com)(?:/?([a-z0-9-]+))?',
    re.IGNORECASE
)


def extract_workable_account(url: str) -> str | None:
    """Return the Workable account slug from a careers URL, or None."""
    if not url:
        return None
    # apply.workable.com/{account}
    m = re.search(r'apply\.workable\.com/([a-z0-9-]+)', url, re.IGNORECASE)
    if m:
        return m.group(1)
    # {account}.workable.com  (legacy subdomain form)
    m = re.search(r'https?://([a-z0-9-]+)\.workable\.com', url, re.IGNORECASE)
    if m and m.group(1) not in ("apply", "www", "jobs"):
        return m.group(1)
    return None


class WorkableAdapter(BaseAdapter):
    ats_type = "workable"

    def fetch_jobs(self) -> list[dict]:
        account = extract_workable_account(self.careers_url)
        if not account:
            logger.error(f"[Workable] Cannot parse account slug from {self.careers_url}")
            return []

        api_url = f"https://apply.workable.com/api/v1/widget/accounts/{account}?details=true"
        r = http_get(api_url)
        if not r:
            raise RuntimeError(f"No response from Workable widget API for account '{account}' ({api_url})")

        try:
            data = r.json()
        except Exception as e:
            raise RuntimeError(f"Invalid JSON from Workable widget API for account '{account}': {e}")

        raw_jobs = data.get("jobs", [])
        self.total_seen = len(raw_jobs)

        jobs = []
        for j in raw_jobs:
            title = j.get("title", "")
            description = j.get("description", "") or ""
            match = classify_job(title, description)
            if not match:
                continue

            city = j.get("city", "") or ""
            country = j.get("country", "") or ""
            loc = ", ".join([p for p in (city, country) if p]) or j.get("location", {}).get("location_str", "")
            remote_flag = "remote" if j.get("telecommuting") else ""
            wt = detect_workplace(title, f"{loc} {remote_flag}", "")
            rs = detect_remote_scope(title, f"{loc} {remote_flag}")

            shortcode = j.get("shortcode", "") or j.get("id", title)
            jobs.append(self.normalize({
                "id": f"wk-{re.sub(r'[^a-z0-9]', '-', str(shortcode).lower())[-40:]}",
                "title": title,
                "url": j.get("url", "") or job_apply_url(account, j),
                "location": loc,
                "workplaceType": wt,
                "remoteScope": rs,
                "matchType": match,
            }))
        return jobs


def job_apply_url(account: str, job: dict) -> str:
    shortcode = job.get("shortcode", "")
    return f"https://apply.workable.com/{account}/j/{shortcode}/" if shortcode else f"https://apply.workable.com/{account}/"
