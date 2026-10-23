import re, logging
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)

def extract_lever_company(url: str) -> str | None:
    m = re.search(r'jobs\.(?:eu\.)?lever\.co/([^/?#]+)', url)
    return m.group(1) if m else None


def lever_api_base(url: str) -> str:
    """Los tableros europeos (jobs.eu.lever.co/<slug>) se sirven desde api.eu.lever.co; el host
    global devuelve un tablero vacío para ellos (por eso Frontier daba «ok» con 0 ofertas)."""
    return "https://api.eu.lever.co" if re.search(r'jobs\.eu\.lever\.co', url) else "https://api.lever.co"


class LeverAdapter(BaseAdapter):
    ats_type = "lever"

    def fetch_jobs(self) -> list[dict]:
        company = extract_lever_company(self.careers_url)
        if not company:
            # Antes devolvía [] y el estado quedaba «ok»: un fallo de configuración parecía «0 ofertas».
            raise RuntimeError(f"[Lever] Cannot parse company from {self.careers_url}")

        api_url = f"{lever_api_base(self.careers_url)}/v0/postings/{company}?mode=json"
        r = http_get(api_url)
        if not r:
            raise RuntimeError(f"No response from Lever API for company '{company}' ({api_url})")

        try:
            data = r.json()
        except Exception as e:
            raise RuntimeError(f"Invalid JSON from Lever API for company '{company}': {e}")

        jobs = []
        self.total_seen = len(data)
        for j in data:
            title = j.get("text", "")
            categories = j.get("categories", {})
            loc = categories.get("location", "") or j.get("hostedUrl", "")
            commitment = categories.get("commitment", "")
            match = classify_job(title, j.get("descriptionPlain", ""))
            if not match:
                continue
            wt = detect_workplace(title, loc, commitment)
            rs = detect_remote_scope(title, loc)
            jobs.append(self.normalize({
                "id": f"lv-{j['id']}",
                "title": title,
                "url": j.get("hostedUrl", ""),
                "location": loc,
                "workplaceType": wt,
                "remoteScope": rs,
                "matchType": match,
                "description": j.get("descriptionPlain", ""),
            }))
        return jobs
