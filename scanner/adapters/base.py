from abc import ABC, abstractmethod
from typing import Optional
import requests, time, logging
from ..company_category import classify_company_category
from ..classify import enrich_job

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

    # True for adapters backed by a real structured API (Greenhouse, Lever,
    # Ashby, SmartRecruiters, Recruitee, Personio, Workday, Workable): if
    # one of these returns 0 postings, that's a TRUSTWORTHY "this company
    # genuinely has zero open positions right now" signal, not a parsing
    # failure — the API either works or raises/errors, there's no
    # ambiguous middle ground like there is with HTML scraping.
    #
    # False for adapters that scrape HTML heuristically (CustomHtmlAdapter,
    # TeamtailorAdapter): 0 candidates found there is genuinely ambiguous
    # between "this company has no postings" and "this page needs
    # JavaScript we can't run" or "our link-matching heuristic missed
    # them" — so it's still worth a "needsReview" flag in that case.
    uses_reliable_api: bool = True

    # True si la última llamada a fetch_jobs() devolvió un resultado parcial
    # (paginación cortada, páginas posteriores fallidas...). Un resultado
    # incompleto NUNCA puede usarse para cerrar ofertas (ver lifecycle.py).
    incomplete: bool = False

    def __init__(self, company: dict):
        self.company = company["name"]
        self.careers_url = company["careersUrl"]
        self.raw = company
        self.total_seen = 0

    @abstractmethod
    def fetch_jobs(self) -> list[dict]:
        """Return list of normalized job dicts."""
        pass

    def normalize(self, raw: dict) -> dict:
        job = {
            "id": raw.get("id", ""),
            "company": self.company,
            "title": raw.get("title", ""),
            "url": raw.get("url", ""),
            "location": raw.get("location", ""),
            "workplaceType": raw.get("workplaceType", "unknown"),
            "remoteScope": raw.get("remoteScope", "unknown"),
            "ats": self.ats_type,
            "matchType": raw.get("matchType", "exactMatch"),
            "companyCategory": classify_company_category(self.company, self.raw.get("category")),
            "viaAggregator": False,
            "firstSeen": raw.get("firstSeen", ""),
            "lastSeen": raw.get("lastSeen", ""),
            "status": "active",
        }
        # La descripción oficial (si el adaptador la tiene) solo sirve para
        # extraer evidencia de contrato/elegibilidad; no se guarda en el JSON.
        return enrich_job(job, raw.get("description", ""))
