"""EA/Respawn: the employer's paginated public HTML search, not an aggregator."""
import re
from urllib.parse import urlparse, urlencode, urlunparse, parse_qs, urljoin
from bs4 import BeautifulSoup
from .base import BaseAdapter, http_get
from ..filters import classify_job, detect_workplace, detect_remote_scope

MAX_PAGES = 20


class EaAdapter(BaseAdapter):
    ats_type = "custom"
    uses_reliable_api = False

    def fetch_jobs(self):
        results, visited_jobs = [], set()
        for term in ("VFX", "effects"):
            parsed = urlparse(self.careers_url)
            if parsed.hostname != "jobs.ea.com":
                raise RuntimeError("EA adapter requires the verified jobs.ea.com portal")
            query = parse_qs(parsed.query)
            query.update(search=[term], jobRecordsPerPage=["20"])
            url = urlunparse(parsed._replace(path="/en_US/careers/SearchJobs/", query=urlencode(query, doseq=True)))
            visited_pages = set()
            for _ in range(MAX_PAGES):
                if url in visited_pages:
                    self.incomplete = True
                    break
                visited_pages.add(url)
                response = http_get(url)
                if response is None:
                    if len(visited_pages) == 1:
                        raise RuntimeError(f"No response from EA search: {url}")
                    self.incomplete = True
                    break
                soup = BeautifulSoup(response.content, "html.parser")
                cards = soup.select("article.article--result")
                if not cards and not soup.select(".results") and not re.search(r"no (?:jobs|results|positions|opportunities)", soup.get_text(" "), re.I):
                    raise RuntimeError("EA search layout not recognized; cannot confirm empty results")
                self.listing_verified = True
                for card in cards:
                    a = card.select_one('a.link_result[href*="/JobDetail/"]')
                    if a is None:
                        self.incomplete = True
                        continue
                    job_url = urljoin(url, a["href"])
                    if urlparse(job_url).hostname != "jobs.ea.com":
                        self.incomplete = True
                        continue
                    if job_url in visited_jobs:
                        continue
                    visited_jobs.add(job_url)
                    self.total_seen += 1
                    title = a.get_text(" ", strip=True)
                    if not classify_job(title, "VFX particle system"):
                        continue
                    studio_el = card.select_one(".list-item-department")
                    studio = studio_el.get_text(" ", strip=True) if studio_el else ""
                    wanted = self.raw.get("studioFilter")
                    excluded = self.raw.get("excludeStudios", [])
                    # Scope is checked locally as well as in the employer's URL filters.
                    if wanted and wanted.lower() not in studio.lower():
                        continue
                    if any(x.lower() in studio.lower() for x in excluded):
                        continue
                    detail = http_get(job_url)
                    if detail is None:
                        self.incomplete = True
                        continue
                    page = BeautifulSoup(detail.content, "html.parser")
                    main = page.select_one("main")
                    if main is None or page.select_one("h1") is None:
                        self.incomplete = True
                        continue
                    fields = {}
                    for field in page.select(".article__content__view__field"):
                        label = field.select_one(".article__content__view__field__label")
                        value = field.select_one(".article__content__view__field__value")
                        if label and value:
                            fields[label.get_text(" ", strip=True).rstrip(":")] = value.get_text(" ", strip=True)
                    actual_studio = fields.get("Studio/Department", studio)
                    if wanted and wanted.lower() not in actual_studio.lower():
                        self.incomplete = True
                        continue
                    if any(x.lower() in actual_studio.lower() for x in excluded):
                        continue
                    text = main.get_text(" ", strip=True)
                    match = classify_job(title, text)
                    if not match:
                        continue
                    location_el = card.select_one(".list-item-location")
                    location = fields.get("Locations", location_el.get_text(" ", strip=True) if location_el else "")
                    ident = re.search(r"/(\d+)(?:[/?#]|$)", urlparse(job_url).path)
                    if not ident:
                        self.incomplete = True
                        continue
                    results.append(self.normalize({
                        "id": "ea-" + ident.group(1), "title": title, "url": job_url,
                        "location": location, "description": text,
                        "workplaceType": detect_workplace(title, location, fields.get("Work Model", "")),
                        "remoteScope": detect_remote_scope(title, location), "matchType": match,
                    }))
                next_link = next((a for a in soup.select('a[href]') if a.get_text(" ", strip=True).lower().startswith("next")), None)
                if next_link is None:
                    break
                url = urljoin(url, next_link["href"])
                if urlparse(url).hostname != "jobs.ea.com" or "/careers/SearchJobs" not in urlparse(url).path:
                    self.incomplete = True
                    break
            else:
                self.incomplete = True
        return results
