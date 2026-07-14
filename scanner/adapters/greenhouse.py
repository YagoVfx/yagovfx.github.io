

import re, logging
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)

def extract_greenhouse_board(url: str) -> str | None:
    # boards.greenhouse.io/BOARD  or  job-boards.greenhouse.io/BOARD
    m = re.search(r'greenhouse\.io/([^/?#]+)', url)
    return m.group(1) if m else None


class GreenhouseAdapter(BaseAdapter):
    ats_type = "greenhouse"

    def fetch_jobs(self) -> list[dict]:
        board = extract_greenhouse_board(self.careers_url)
        if not board:
            logger.error(f"[Greenhouse] Cannot parse board from {self.careers_url}")
            return []

        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
        r = http_get(api_url)
        if not r:
            return []

        try:
            data = r.json()
        except Exception:
            return []

        jobs = []
        for j in data.get("jobs", []):
            title = j.get("title", "")
            match = classify_job(title, j.get("content", ""))
            if not match:
                continue
            loc = j.get("location", {}).get("name", "")
            wt = detect_workplace(title, loc, j.get("metadata", []))
            rs = detect_remote_scope(title, loc)
            jobs.append(self.normalize({
                "id": f"gh-{j['id']}",
                "title": title,
                "url": j.get("absolute_url", ""),
                "location": loc,
                "workplaceType": wt,
                "remoteScope": rs,
                "matchType": match,
            }))
        return jobs

