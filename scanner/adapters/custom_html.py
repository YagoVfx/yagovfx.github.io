import re, logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)


class CustomHtmlAdapter(BaseAdapter):
    ats_type = "custom"

    def fetch_jobs(self) -> list[dict]:
        r = http_get(self.careers_url)
        if not r:
            return []

        soup = BeautifulSoup(r.text, "lxml")
        base = f"{urlparse(self.careers_url).scheme}://{urlparse(self.careers_url).netloc}"
        seen = set()
        jobs = []
        candidates_seen = 0

        for a in soup.find_all("a", href=True):
            href = a["href"]
            title = a.get_text(separator=" ", strip=True)
            title = re.sub(r'\s+', ' ', title)
            if not title or len(title) < 5 or len(title) > 120:
                continue
            candidates_seen += 1

            match = classify_job(title, "")
            if not match:
                continue

            full_url = urljoin(base, href)
            if full_url in seen:
                continue
            seen.add(full_url)

            safe_id = re.sub(r'[^a-z0-9]', '-', full_url.lower())[-40:]
            jobs.append(self.normalize({
                "id": f"ch-{safe_id}",
                "title": title,
                "url": full_url,
                "location": "",
                "workplaceType": "unknown",
                "remoteScope": "unknown",
                "matchType": match,
            }))

        self.total_seen = candidates_seen
        return jobs
