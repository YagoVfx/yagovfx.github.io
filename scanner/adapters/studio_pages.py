"""Verified bespoke employer listings; unexpected markup is a failure, not zero jobs."""
import hashlib
from bs4 import BeautifulSoup
from .base import BaseAdapter, http_get
from ..filters import classify_job


class InfinitePlusAdapter(BaseAdapter):
    ats_type = "custom"
    uses_reliable_api = False

    def fetch_jobs(self):
        response = http_get(self.careers_url)
        if response is None:
            raise RuntimeError("Infinite Plus careers unavailable")
        soup = BeautifulSoup(response.text, "html.parser")
        panels = soup.select("button.accordion + .panel")
        if not panels or "Infinite Plus" not in soup.get_text():
            raise RuntimeError("Infinite Plus listing schema changed")
        jobs = []
        for panel in panels:
            title_node = panel.find_previous_sibling().select_one(".elementor-col-30")
            if title_node is None or not panel.get_text(strip=True):
                self.incomplete = True
                continue
            self.total_seen += 1
            title = title_node.get_text(" ", strip=True)
            match = classify_job(title)
            if not match:
                continue
            job = self.normalize({
                "id": "infiniteplus-" + hashlib.sha256(title.encode()).hexdigest()[:16],
                "title": title, "description": panel.get_text(" ", strip=True),
                "url": self.careers_url, "matchType": match,
            })
            # The employer publishes the full descriptions inline, without detail URLs.
            job.update(urlIsLanding=True, directUrl=False)
            jobs.append(job)
        self.listing_verified = not self.incomplete
        return jobs


class MercurySteamAdapter(BaseAdapter):
    ats_type = "custom"
    uses_reliable_api = False

    def fetch_jobs(self):
        response = http_get(self.careers_url)
        if response is None:
            raise RuntimeError("MercurySteam careers unavailable")
        soup = BeautifulSoup(response.content, "html.parser")
        text = soup.get_text(" ", strip=True)
        # Explicit employer statement, verified on its public talent page.
        # When vacancies appear this adapter requires review instead of silently
        # interpreting unrecognized HTML as a complete empty listing.
        if "MercurySteam" not in text or "Hoy no tenemos posiciones abiertas." not in text:
            raise RuntimeError("MercurySteam no longer confirms an empty board; review new listing")
        self.listing_verified = True
        return []
