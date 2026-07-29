import re, logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)

JOB_KEYWORD_RE = re.compile(r'/(?:jobs?|careers?|positions?|openings?|vacanc(?:y|ies)|roles?)(?:[/?#-]|$)', re.IGNORECASE)
JOB_SPECIFIC_RE = re.compile(r'\d{3,}|(?:[a-z0-9]+-){2,}[a-z0-9]+', re.IGNORECASE)

TITLE_HEADING_SELECTOR = re.compile(r'title|position|job-?name|role', re.IGNORECASE)


def _looks_like_job_url(href: str) -> bool:
    return bool(JOB_KEYWORD_RE.search(href) and JOB_SPECIFIC_RE.search(href))


def _extract_title(a_tag) -> str:
    """The <a> tag's own text is usually the job title, but on some sites
    it's short/generic (an icon, "Learn more", empty) and the real title
    sits in a nearby heading element instead. Fall back to searching the
    anchor's parent chain for a heading-like element when the anchor text
    itself looks too short or generic to be a real job title.
    """
    own_text = re.sub(r'\s+', ' ', a_tag.get_text(separator=" ", strip=True)).strip()
    if len(own_text) >= 8:
        return own_text

    parent = a_tag.find_parent()
    for _ in range(3):  # walk up a few levels at most
        if not parent:
            break
        heading = parent.find(['h1', 'h2', 'h3', 'h4', 'h5'])
        if not heading:
            heading = parent.find(class_=TITLE_HEADING_SELECTOR)
        if heading:
            heading_text = re.sub(r'\s+', ' ', heading.get_text(separator=" ", strip=True)).strip()
            if len(heading_text) >= 8:
                return heading_text
        parent = parent.find_parent()

    return own_text


class CustomHtmlAdapter(BaseAdapter):
    ats_type = "custom"
    uses_reliable_api = False  # HTML-scraping heuristic, 0 found is ambiguous

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

            title = _extract_title(a)
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
