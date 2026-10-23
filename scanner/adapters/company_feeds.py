"""Public feeds actually embedded by Room 8, Ember Lab and Build A Rocket Boy.

Endpoints verified from their public careers HTML/JS on 2026-10-23. These
are structured employer feeds, including valid empty responses.
"""
from urllib.parse import urlparse
from html import unescape
from bs4 import BeautifulSoup
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope


def plain(html):
    if isinstance(html, str) and "<" not in html:
        return unescape(html)
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


class BambooAdapter(BaseAdapter):
    ats_type = "custom"

    def fetch_jobs(self):
        host = urlparse(self.careers_url).hostname or ""
        if not host.endswith(".bamboohr.com"):
            raise RuntimeError("BambooHR requires a verified company subdomain")
        response = http_get(f"https://{host}/jobs/embed2.php?version=1.0.0&format=json")
        if response is None:
            raise RuntimeError("No response from BambooHR employer feed")
        data = response.json()
        if data.get("success") is not True or not isinstance(data.get("departments"), list):
            raise RuntimeError("BambooHR feed schema not recognized")
        jobs = []
        for department in data["departments"]:
            if not isinstance(department.get("positions"), list):
                raise RuntimeError("BambooHR positions missing")
            for j in department["positions"]:
                self.total_seen += 1
                title, location = j.get("name", ""), j.get("location", "")
                match = classify_job(title)
                if not match:
                    continue
                if urlparse(j.get("url", "")).hostname != host:
                    self.incomplete = True
                    continue
                detail = http_get(j["url"])
                if detail is None:
                    self.incomplete = True
                    continue
                jobs.append(self.normalize({"id": f"bamboo-{host.split('.')[0]}-{j['id']}",
                    "title": title, "url": j["url"], "location": location,
                    "description": plain(detail.content), "matchType": match,
                    "workplaceType": detect_workplace(title, location),
                    "remoteScope": detect_remote_scope(title, location)}))
        return jobs


class PinpointAdapter(BaseAdapter):
    ats_type = "custom"

    def fetch_jobs(self):
        host = urlparse(self.careers_url).hostname or ""
        if not host.endswith(".pinpointhq.com"):
            raise RuntimeError("Pinpoint requires a verified company subdomain")
        response = http_get(f"https://{host}/en/postings.json")
        if response is None:
            raise RuntimeError("No response from Pinpoint employer feed")
        data = response.json()
        if not isinstance(data.get("data"), list):
            raise RuntimeError("Pinpoint feed schema not recognized")
        if data.get("links", {}).get("next"):
            self.incomplete = True
        jobs = []
        self.total_seen = len(data["data"])
        for row in data["data"]:
            j = row.get("attributes", row)
            title, url = j.get("title"), j.get("url")
            # Empty board verified live. A changed nonempty schema must not
            # silently become a complete zero-result scan.
            if not isinstance(title, str) or not isinstance(url, str):
                self.incomplete = True
                continue
            match = classify_job(title)
            if not match:
                continue
            if urlparse(url).hostname != host:
                self.incomplete = True
                continue
            detail = http_get(url)
            if detail is None:
                self.incomplete = True
                continue
            text = plain(detail.content)
            jobs.append(self.normalize({"id": f"pinpoint-{host.split('.')[0]}-{row['id']}",
                "title": title, "url": url, "description": text, "matchType": match,
                "location": "", "workplaceType": detect_workplace(title, "", text), "remoteScope": "unknown"}))
        return jobs


class Room8Adapter(BaseAdapter):
    ats_type = "custom"
    HOSTS = ("room8group.com", "room8studio.com")

    def fetch_jobs(self):
        jobs = []
        for host in self.HOSTS:
            for page in range(1, 11):
                response = http_get(f"https://{host}/wp-json/wp/v2/talent?per_page=100&_embed=true&page={page}")
                if response is None:
                    if page == 1:
                        raise RuntimeError(f"No response from Room 8 official feed: {host}")
                    self.incomplete = True
                    break
                rows = response.json()
                if not isinstance(rows, list):
                    raise RuntimeError("Room 8 feed schema not recognized")
                self.total_seen += len(rows)
                for j in rows:
                    title = plain(j.get("title", {}).get("rendered", ""))
                    description = plain(j.get("content", {}).get("rendered", ""))
                    match = classify_job(title, description)
                    if not match:
                        continue
                    if urlparse(j.get("link", "")).hostname != host:
                        self.incomplete = True
                        continue
                    terms = [t for group in j.get("_embedded", {}).get("wp:term", []) for t in group]
                    location = ", ".join(t["name"] for t in terms if t.get("taxonomy") == "tlocation")
                    cooperation = " ".join(t["name"] for t in terms if t.get("taxonomy") == "tcoop")
                    description += " " + cooperation
                    jobs.append(self.normalize({"id": f"r8-{host.split('.')[0]}-{j['id']}",
                        "title": title, "url": j["link"], "location": location,
                        "description": description, "matchType": match,
                        "workplaceType": detect_workplace(title, location, cooperation),
                        "remoteScope": detect_remote_scope(title, location),
                        "postedDate": j.get("date_gmt", "") + "Z" if j.get("date_gmt") else None}))
                pages = response.headers.get("X-WP-TotalPages")
                if pages and page >= int(pages):
                    break
                if not pages:
                    self.incomplete = True
                    break
            else:
                self.incomplete = True
        return jobs
