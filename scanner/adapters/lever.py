
import re, logging
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)

def extract_lever_company(url: str) -> str | None:
    m = re.search(r'jobs\.lever\.co/([^/?#]+)', url)
    return m.group(1) if m else None


class LeverAdapter(BaseAdapter):
    ats_type = "lever"

    def fetch_jobs(self) -> list[dict]:
        company = extract_lever_company(self.careers_url)
        if not company:
            logger.error(f"[Lever] Cannot parse company from {self.careers_url}")
            return []

        api_url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        r = http_get(api_url)
        if not r:
            return []

        try:
            data = r.json()
        except Exception:
            return []

        jobs = []
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
            }))
        return jobs