"""Workable: consulta el tablero p?blico de cada empresa en apply.workable.com.
El portal global jobs.workable.com ignora el antiguo par?metro companyIds y no
se utiliza: podr?a atribuir ofertas de otras empresas a la configurada.
"""
import re
import logging
from bs4 import BeautifulSoup
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)



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

        raise RuntimeError(f"[Workable] Configure a verified apply.workable.com account URL: {self.careers_url}")

    def _job_url(self, workable_url: str, shortcode: str) -> str:
        """If the company config has an optional officialUrlTemplate (set
        by the person in the admin panel, e.g. because they noticed the
        company embeds this same Workable listing on their own domain —
        "https://lighthousegames.com/careers/{shortcode}/" — use that
        instead of the workable.com URL. Same application flow either way
        (Workable is the ATS itself), but it lands on the company's own
        site first rather than workable.com/apply.workable.com directly.
        Falls back to the plain Workable URL if no template is set.
        """
        template = self.raw.get("officialUrlTemplate")
        if template and shortcode:
            try:
                return template.replace("{shortcode}", str(shortcode))
            except Exception:
                pass
        return workable_url

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
            description = BeautifulSoup(j.get("description", "") or "", "html.parser").get_text(" ", strip=True)
            description += " " + (j.get("employment_type") or "")
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
            workable_url = j.get("url", "") or f"https://apply.workable.com/{account}/j/{shortcode}/"
            job = self.normalize({
                "id": f"wk-{re.sub(r'[^a-z0-9]', '-', str(shortcode).lower())[-40:]}",
                "title": title,
                "url": self._job_url(workable_url, shortcode),
                "location": loc,
                "workplaceType": wt,
                "remoteScope": rs,
                "matchType": match,
                "description": description,
                "postedDate": j.get("published_on"),
            })
            existing = next((x for x in jobs if x["id"] == job["id"]), None)
            if existing is None:
                jobs.append(job)
            elif loc and loc not in existing["location"]:
                existing["location"] += "; " + loc
        return jobs

    def _fetch_via_search_portal(self, company_id: str) -> list[dict]:
        raise RuntimeError("Workable global search cannot verify company identity. Configure the company's apply.workable.com account URL.")
