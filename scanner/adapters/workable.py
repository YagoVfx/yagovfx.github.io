"""
Workable adapter.

Workable has TWO different public surfaces, and companies can show up under
either one (or a custom domain wrapping either):

1. The classic per-company "widget" endpoint (most common):
       GET https://apply.workable.com/api/v1/widget/accounts/{account}?details=true
   Career pages look like:
       https://apply.workable.com/{account}/
       https://{account}.workable.com/          (legacy subdomain form)

2. Workable's own cross-company job SEARCH portal (jobs.workable.com),
   which some companies get indexed into with an opaque company ID instead
   of a friendly slug:
       https://jobs.workable.com/company/{companyId}/jobs-at-{name}
   This is a different product with a different API
   (jobs.workable.com/api/v1/jobs, filterable by companyIds) — the classic
   apply.workable.com/{slug} URL may 404 even though the company IS on
   Workable, if their public listing only exists in this portal.

If a company's careers page is on their OWN domain with Workable embedded
via JS (like https://lighthousegames.com/careers/), we can't derive either
identifier from that URL alone — someone has to find the real Workable URL
once (browser devtools Network tab, filter "workable", or just search
"<company> workable jobs") and put that direct URL in companies.json.

NOTE ON THE SEARCH-PORTAL PATH: this one is less publicly documented than
the classic widget endpoint, so the query param name below (`companyIds`)
is a best-effort guess based on the field Workable's own search results
expose, not a confirmed-stable contract. If it stops matching real jobs,
check scanner-status.json's error message (it includes a body snippet) and
adjust ID_SEARCH_PARAM below.
"""
import re
import logging
import requests
from .base import BaseAdapter, http_get, HEADERS, TIMEOUT
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)

ID_SEARCH_PARAM = "companyIds"  # see NOTE above


def extract_workable_account(url: str) -> str | None:
    """Return the classic Workable account slug from a careers URL, or None."""
    if not url:
        return None
    m = re.search(r'apply\.workable\.com/([a-z0-9-]+)', url, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'https?://([a-z0-9-]+)\.workable\.com', url, re.IGNORECASE)
    if m and m.group(1) not in ("apply", "www", "jobs"):
        return m.group(1)
    return None


def extract_jobs_portal_company_id(url: str) -> str | None:
    """Return the opaque company id from a jobs.workable.com/company/{id}/... URL, or None."""
    if not url:
        return None
    m = re.search(r'jobs\.workable\.com/company/([A-Za-z0-9]+)', url)
    return m.group(1) if m else None


class WorkableAdapter(BaseAdapter):
    ats_type = "workable"

    def fetch_jobs(self) -> list[dict]:
        account = extract_workable_account(self.careers_url)
        if account:
            return self._fetch_via_widget(account)

        company_id = extract_jobs_portal_company_id(self.careers_url)
        if company_id:
            return self._fetch_via_search_portal(company_id)

        logger.error(f"[Workable] Cannot parse an account slug or company id from {self.careers_url}")
        return []

    def _fetch_via_widget(self, account: str) -> list[dict]:
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
            loc = ", ".join([p for p in (city, country) if p])
            remote_flag = "remote" if j.get("telecommuting") else ""
            wt = detect_workplace(title, f"{loc} {remote_flag}", "")
            rs = detect_remote_scope(title, f"{loc} {remote_flag}")
            shortcode = j.get("shortcode", "") or j.get("id", title)
            jobs.append(self.normalize({
                "id": f"wk-{re.sub(r'[^a-z0-9]', '-', str(shortcode).lower())[-40:]}",
                "title": title,
                "url": j.get("url", "") or f"https://apply.workable.com/{account}/j/{shortcode}/",
                "location": loc,
                "workplaceType": wt,
                "remoteScope": rs,
                "matchType": match,
            }))
        return jobs

    def _fetch_via_search_portal(self, company_id: str) -> list[dict]:
        api_url = f"https://jobs.workable.com/api/v1/jobs?{ID_SEARCH_PARAM}={company_id}&limit=100"
        try:
            r = requests.get(api_url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            body_snippet = ""
            try:
                body_snippet = f" | body: {r.text[:300]}"
            except Exception:
                pass
            raise RuntimeError(f"Workable search-portal request failed for {api_url}: {e}{body_snippet}")

        raw_jobs = data.get("results") or data.get("jobs") or (data if isinstance(data, list) else [])
        self.total_seen = len(raw_jobs)
        jobs = []
        for j in raw_jobs:
            title = j.get("title", "")
            description = j.get("descriptionText") or j.get("description", "") or ""
            match = classify_job(title, description)
            if not match:
                continue
            loc = j.get("fullLocation") or j.get("locationsText", "") or ""
            wt = detect_workplace(title, f"{loc} {j.get('workplace','')}", "")
            rs = detect_remote_scope(title, loc)
            jid = j.get("id") or j.get("shortcode") or title
            jobs.append(self.normalize({
                "id": f"wk-{re.sub(r'[^a-z0-9]', '-', str(jid).lower())[-40:]}",
                "title": title,
                "url": j.get("url") or j.get("applyUrl") or self.careers_url,
                "location": loc,
                "workplaceType": wt,
                "remoteScope": rs,
                "matchType": match,
            }))
        return jobs
