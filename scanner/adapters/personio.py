"""
Personio adapter.

Every Personio customer has a public, no-auth XML job feed used to power
their own careers page:
    GET https://{company}.jobs.personio.de/xml?language=en
(some accounts are hosted on .com instead of .de — we try both).

No official REST/JSON equivalent is publicly documented; XML is the
supported public feed format for this ATS.
"""
import re
import logging
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)


def extract_personio_subdomain(url: str) -> str | None:
    m = re.search(r'([a-zA-Z0-9_-]+)\.jobs\.personio\.(?:de|com)', url or "")
    return m.group(1) if m else None


class PersonioAdapter(BaseAdapter):
    ats_type = "personio"

    def _fetch_xml(self, subdomain: str):
        for tld in ("de", "com"):
            url = f"https://{subdomain}.jobs.personio.{tld}/xml?language=en"
            r = http_get(url)
            if r and r.status_code == 200 and r.text.strip():
                return r.text
        return None

    def fetch_jobs(self) -> list[dict]:
        subdomain = extract_personio_subdomain(self.careers_url)
        if not subdomain:
            logger.error(f"[Personio] Cannot parse subdomain from {self.careers_url}")
            return []

        xml_text = self._fetch_xml(subdomain)
        if not xml_text:
            raise RuntimeError(f"No response from Personio XML feed for subdomain '{subdomain}'")

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise RuntimeError(f"Invalid XML from Personio feed for subdomain '{subdomain}': {e}")

        positions = root.findall(".//position")
        self.total_seen = len(positions)

        jobs = []
        base_url = f"https://{subdomain}.jobs.personio.de"
        for p in positions:
            title = (p.findtext("name") or "").strip()
            if not title:
                continue
            department = (p.findtext("department") or "")
            description_parts = [jd.findtext("value") or "" for jd in p.findall(".//jobDescription")]
            description = " ".join(description_parts)
            match = classify_job(f"{title} {department}", description)
            if not match:
                continue

            office = (p.findtext("office") or "")
            schedule = (p.findtext("schedule") or "")
            wt = detect_workplace(title, f"{office} {schedule}", description[:200])
            rs = detect_remote_scope(title, office)

            pos_id = p.get("id") or title
            jobs.append(self.normalize({
                "id": f"pr-{re.sub(r'[^a-z0-9]', '-', str(pos_id).lower())[-40:]}",
                "title": title,
                "url": f"{base_url}/job/{pos_id}",
                "location": office,
                "workplaceType": wt,
                "remoteScope": rs,
                "matchType": match,
            }))
        return jobs
