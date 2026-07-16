import re, logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)

# A link only counts as a "job candidate" if its URL both (a) contains a
# job/career-ish keyword AND (b) also contains a signal that this is a
# SPECIFIC posting — a numeric id (3+ digits) or a multi-word hyphenated
# slug — rather than just a generic section of the site. This matters a lot
# on career sites where the ENTIRE domain lives under /careers/ (e.g. Oracle
# Taleo instances like jobs.ea.com): there, every nav link, filter, and
# footer link also contains "/careers/", so keyword-matching alone massively
# overcounts (we saw 46 "postings" on a page with 13 real ones).
JOB_KEYWORD_RE = re.compile(r'/(?:jobs?|careers?|positions?|openings?|vacanc(?:y|ies)|roles?)(?:[/?#-]|$)', re.IGNORECASE)
JOB_SPECIFIC_RE = re.compile(r'\d{3,}|(?:[a-z0-9]+-){2,}[a-z0-9]+', re.IGNORECASE)


def _looks_like_job_url(href: str) -> bool:
    return bool(JOB_KEYWORD_RE.search(href) and JOB_SPECIFIC_RE.search(href))


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
            if not _looks_like_job_url(href):
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
