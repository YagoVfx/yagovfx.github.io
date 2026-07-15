from abc import ABC, abstractmethod
from typing import Optional
import requests, time, logging

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "VFXJobsBot/1.0 (portfolio job tracker; contact via GitHub)"
}
TIMEOUT = 15
RETRY_WAIT = 5

def http_get(url: str, retries: int = 2) -> Optional[requests.Response]:
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 429:
                logger.warning(f"Rate limited on {url}, waiting {RETRY_WAIT}s")
                time.sleep(RETRY_WAIT)
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt+1} failed for {url}: {e}")
            if attempt < retries:
                time.sleep(2)
    return None


class BaseAdapter(ABC):
    ats_type: str = "base"

    def __init__(self, company: dict):
        self.company = company["name"]
        self.careers_url = company["careersUrl"]
        self.raw = company
        # Total postings this adapter actually saw on the page/API, BEFORE
        # filtering by the VFX regex. Lets the scanner tell apart "this
        # company genuinely has 0 VFX openings right now" (total_seen > 0,
        # jobsFound == 0) from "the parser saw nothing at all — probably
        # broken/blocked/JS-rendered" (total_seen == 0).
        self.total_seen = 0

    @abstractmethod
    def fetch_jobs(self) -> list[dict]:
        """Return list of normalized job dicts."""
        pass

    def normalize(self, raw: dict) -> dict:
        return {
            "id": raw.get("id", ""),
            "company": self.company,
            "title": raw.get("title", ""),
            "url": raw.get("url", ""),
            "location": raw.get("location", ""),
            "workplaceType": raw.get("workplaceType", "unknown"),
            "remoteScope": raw.get("remoteScope", "unknown"),
            "ats": self.ats_type,
            "matchType": raw.get("matchType", "exactMatch"),
            "firstSeen": raw.get("firstSeen", ""),
            "lastSeen": raw.get("lastSeen", ""),
            "status": "active",
        }
