"""
Adapter for Massive Entertainment's careers page (massive.se/career/).

Not a known third-party ATS — it's a WordPress theme with a custom
paginated "Load More" AJAX endpoint:

    POST https://www.massive.se/wp-content/themes/massive/inc/ajax.php
    Content-Type: application/x-www-form-urlencoded
    Body: action=get_jobs&paged={page_number}

Discovered via the browser's Network tab (no public documentation for
this — it's specific to this WordPress theme/site). Confirmed public,
unauthenticated, no key needed.

Response shape:
    {"success": true, "data": {"jobs": ["<a href=...>...</a>", ...], "paging": false}}

Each item in "jobs" is a raw HTML fragment (an <a> tag with nested divs),
not structured JSON — so we still need a light regex/HTML parse per item,
same spirit as CustomHtmlAdapter but targeted at a known, reliable
endpoint instead of guessing at page structure. "paging" tells us whether
there's a next page (false means we've reached the end).

NOTE: this adapter is Massive-specific (URL is hardcoded to massive.se —
no company parameter of any kind was seen in the request). If other
Ubisoft-family studios turn out to share the same WordPress theme (the
job-row CSS classes — "jobs__row", "jobs__title" — suggest a shared
template), this file would need to be generalized to accept a base URL
per company rather than assuming massive.se. Not attempted here since we
only have confirmed request/response data for Massive itself.
"""
import re
import logging
import requests
from bs4 import BeautifulSoup
from .base import BaseAdapter, HEADERS, TIMEOUT
from ..filters import classify_job, detect_workplace, detect_remote_scope

logger = logging.getLogger(__name__)

AJAX_URL = "https://www.massive.se/wp-content/themes/massive/inc/ajax.php"
MAX_PAGES = 10  # safety cap


class MassiveWPAdapter(BaseAdapter):
    ats_type = "massive-wp"
    uses_reliable_api = True  # structured AJAX endpoint, not blind HTML scraping

    def fetch_jobs(self) -> list[dict]:
        jobs = []
        seen_urls = set()

        for page in range(1, MAX_PAGES + 1):
            try:
                r = requests.post(
                    AJAX_URL,
                    data={"action": "get_jobs", "paged": page},
                    headers=HEADERS,
                    timeout=TIMEOUT,
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                if page == 1:
                    raise RuntimeError(f"No response from Massive careers AJAX endpoint: {e}")
                logger.warning(f"[MassiveWP] Page {page} failed: {e} — stopping pagination")
                break

            raw_jobs = (data.get("data") or {}).get("jobs", [])
            if not raw_jobs:
                break
            self.total_seen += len(raw_jobs)

            for fragment in raw_jobs:
                soup = BeautifulSoup(fragment, "lxml")
                a = soup.find("a")
                if not a:
                    continue
                url = a.get("href", "")
                title_tag = a.find("h4")
                title = (title_tag.get_text(strip=True) if title_tag else a.get("title", "")) or ""
                if not title or not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                # The small "family, location, project" line sits in the
                # first <div> under the title on mobile — reuse it as
                # location context for our workplace/scope detection.
                meta_div = soup.find("div", class_=re.compile(r"d-xs-block"))
                meta_text = meta_div.get_text(" ", strip=True) if meta_div else ""

                match = classify_job(title, meta_text)
                if not match:
                    continue

                wt = detect_workplace(title, meta_text, "")
                rs = detect_remote_scope(title, meta_text)
                safe_id = re.sub(r"[^a-z0-9]", "-", url.lower())[-40:]
                jobs.append(self.normalize({
                    "id": f"mwp-{safe_id}",
                    "title": title,
                    "url": url,
                    "location": meta_text,
                    "workplaceType": wt,
                    "remoteScope": rs,
                    "matchType": match,
                }))

            paging = (data.get("data") or {}).get("paging", False)
            if not paging:
                break

        return jobs
