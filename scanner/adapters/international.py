"""Employer-owned listings for Capcom (HRMOS) and Rovio's own careers site."""
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from .base import BaseAdapter, http_get
from ..filters import classify_job


class CapcomAdapter(BaseAdapter):
    ats_type = 'custom'
    uses_reliable_api = False

    def fetch_jobs(self):
        response = http_get(self.careers_url)
        if response is None:
            raise RuntimeError('Capcom HRMOS listing unavailable')
        soup = BeautifulSoup(response.content, 'html.parser')
        links = {a['href']: a for a in soup.select('a[href]')
                 if re.fullmatch(r'https://hrmos\.co/pages/capcom/jobs/[\w-]+', a['href'])}
        if not links:
            raise RuntimeError('Capcom HRMOS listing schema changed')
        self.total_seen = len(links)
        self.listing_verified = True
        self.incomplete = bool(soup.select('a[rel="next"], a[href*="page="]'))
        jobs = []
        for url, anchor in links.items():
            heading = anchor.find('h2')
            if heading is None:
                self.incomplete = True
                continue
            original = heading.get_text(' ', strip=True)
            # Preserve the Japanese title; add only an explicit role translation.
            title = ('VFX Artist — ' + original if 'エフェクトデザイナー' in original else
                     'Technical Artist — ' + original if 'テクニカルアーティスト' in original else original)
            match = classify_job(title)
            if not match:
                continue
            detail = http_get(url)
            if detail is None:
                self.incomplete = True
                continue
            body = BeautifulSoup(detail.content, 'html.parser')
            location = 'Japan'
            for label in body.find_all(['th', 'dt']):
                if '勤務地' in label.get_text():
                    value = label.find_next_sibling(['td', 'dd'])
                    if value:
                        text = value.get_text(' ', strip=True)
                        cities = [city for jp, city in [('大阪', 'Osaka'), ('東京', 'Tokyo')] if jp in text]
                        location = ', '.join(cities + ['Japan'])
            jobs.append(self.normalize({'id': 'capcom-' + url.rsplit('/', 1)[-1], 'title': title,
                'url': url, 'location': location, 'description': body.get_text(' ', strip=True), 'matchType': match}))
        return jobs


class RovioAdapter(BaseAdapter):
    ats_type = 'custom'
    uses_reliable_api = False

    def fetch_jobs(self):
        response = http_get(self.careers_url)
        if response is None:
            raise RuntimeError('Rovio official listing unavailable')
        soup = BeautifulSoup(response.content, 'html.parser')
        links = {a['href']: a for a in soup.select('a[href]')
                 if urlparse(a['href']).hostname == 'www.rovio.com'
                 and re.fullmatch(r'/open-positions/[^/]+/', urlparse(a['href']).path)}
        if not links:
            raise RuntimeError('Rovio listing unrecognized or empty; review required')
        self.listing_verified = True
        self.total_seen = len(links)
        self.incomplete = bool(soup.select('a[rel="next"]'))
        jobs = []
        for url, anchor in links.items():
            title = anchor.get_text(' ', strip=True)
            match = classify_job(title)
            if not match:
                continue
            detail = http_get(url)
            if detail is None:
                self.incomplete = True
                continue
            body = BeautifulSoup(detail.content, 'html.parser')
            jobs.append(self.normalize({'id': 'rovio-' + url.rstrip('/').rsplit('/', 1)[-1],
                'title': title, 'url': url, 'location': '', 'description': body.get_text(' ', strip=True), 'matchType': match}))
        return jobs
