import re, logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)

# A link only counts as a "job candidate" if its URL actually looks like a
# job/career/position/vacancy link. Just having plausible-length link text
# is NOT enough — normal nav/footer/social links pass that check too, which
# made total_seen (and therefore "needsReview") meaningless on JS-heavy
# corporate sites: we'd count dozens of menu links as "postings seen" even
# though the real job data never rendered (it's injected by JS we can't run).
JOB_URL_RE = re.compile(
    r'/(jobs?|careers?|positions?|openings?|vacanc(?:y|ies)|roles?)(?:[/?#]|$)',
    re.IGNORECASE
)


class CustomHtmlAdapter(BaseAdapter):
    ats_type = "custom"

    def fetch_jobs(self) -> list[dict]:
        r = http_get(self.careers_url)
        if not r:
            raise RuntimeError(f"No response from {self.careers_url}")

        soup = BeautifulSoup(r.text, "lxml")
        base = f"{urlparse(self.careers_url).scheme}://{urlparse(self.careers_url).netloc}"
        seen = set()
        jobs = []
        candidates_seen = 0

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not JOB_URL_RE.search(href):
                continue

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
