"""Read the paginated API used by Epic's own public careers page.

Endpoint and limit/skip parameters verified in the JS referenced by
https://www.epicgames.com/site/en-US/careers/jobs on 2026-10-23.
"""
from bs4 import BeautifulSoup
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

ENDPOINT = "https://greenhouse-service.debc.live.use1a.on.epicgames.com/api/job"
PAGE_SIZE, MAX_PAGES = 100, 20


class EpicAdapter(BaseAdapter):
    ats_type = "greenhouse"

    def fetch_jobs(self):
        jobs, seen = [], set()
        for page in range(MAX_PAGES):
            response = http_get(f"{ENDPOINT}?limit={PAGE_SIZE}&skip={page * PAGE_SIZE}&page={page + 1}")
            if response is None:
                if page == 0:
                    raise RuntimeError("No response from Epic careers API")
                self.incomplete = True
                break
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get("hits"), list) or not isinstance(data.get("total"), int):
                raise RuntimeError("Epic careers API response layout not recognized")
            hits = data["hits"]
            new = [j for j in hits if j.get("id") not in seen]
            if not new and len(seen) < data["total"]:
                self.incomplete = True
                break
            for j in new:
                seen.add(j["id"])
                title = j.get("title", "")
                match = classify_job(title, "")
                if not match:
                    continue
                detail = http_get(f"{ENDPOINT}/{j['id']}")
                if detail is None:
                    self.incomplete = True
                    continue
                full = detail.json()
                if not isinstance(full, dict):
                    self.incomplete = True
                    continue
                description = BeautifulSoup(full.get("content", ""), "html.parser").get_text(" ", strip=True)
                loc = j.get("location", {})
                location = loc.get("name", "") if isinstance(loc, dict) else str(loc)
                jobs.append(self.normalize({
                    "id": f"gh-{j['id']}", "title": title,
                    "url": j.get("absolute_url", ""), "location": location,
                    "description": description,
                    "workplaceType": "remote" if j.get("remote") is True else detect_workplace(title, location, ""),
                    "remoteScope": detect_remote_scope(title, location), "matchType": match,
                    "postedDate": full.get("first_published") or j.get("first_published"),
                }))
            if len(seen) >= data["total"]:
                break
        else:
            self.incomplete = True
        self.total_seen = len(seen)
        return jobs
