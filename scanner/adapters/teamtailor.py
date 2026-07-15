import re, logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)

JOB_LINK_PATTERNS = [r'/jobs/\d+', r'/jobs/[a-z0-9-]+', r'/en/jobs/']


class TeamtailorAdapter(BaseAdapter):
    ats_type = "teamtailor"

    def _get_jobs_page(self) -> str | None:
        candidates = [
            self.careers_url.rstrip('/'),
            self.careers_url.rstrip('/') + '/jobs',
            self.careers_url.rstrip('/') + '/en/jobs',
        ]
        for url in candidates:
            r = http_get(url)
            if r and r.status_code == 200:
                return r.text
        return None

    def fetch_jobs(self) -> list[dict]:
        html = self._get_jobs_page()
        if not html:
            raise RuntimeError(f"No response from any Teamtailor URL candidate for {self.careers_url}")

        soup = BeautifulSoup(html, "lxml")
        base = f"{urlparse(self.careers_url).scheme}://{urlparse(self.careers_url).netloc}"
        seen_urls = set()
        jobs = []
        candidates_seen = 0

        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base, href)
            if full_url in seen_urls:
                continue
            if not any(re.search(p, href) for p in JOB_LINK_PATTERNS):
                continue
            seen_urls.add(full_url)
            candidates_seen += 1

            title = (a.get("aria-label") or a.get_text(separator=" ", strip=True))
            title = re.sub(r'\s+', ' ', title).strip()
            if not title or len(title) < 3:
                continue

            loc = ""
            parent = a.find_parent()
            if parent:
                loc_el = parent.find(class_=re.compile(r'location|city|place', re.I))
                if loc_el:
                    loc = loc_el.get_text(strip=True)

            match = classify_job(title, "")
            if not match:
                continue

            wt = detect_workplace(title, loc, "")
            rs = detect_remote_scope(title, loc)
            safe_id = re.sub(r'[^a-z0-9]', '-', full_url.lower())
            jobs.append(self.normalize({
                "id": f"tt-{safe_id[-40:]}",
                "title": title,
                "url": full_url,
                "location": loc,
                "workplaceType": wt,
                "remoteScope": rs,
                "matchType": match,
            }))

        self.total_seen = candidates_seen
        return jobs
