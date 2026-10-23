"""
Adaptadores para webs OFICIALES de estudios que no usan ATS (investigados y verificados el
2026-10-21 con las propias páginas de carreras; ver EMPRESAS_Y_FUENTES.md).

Son fuentes poco fiables por naturaleza (HTML sin API): uses_reliable_api=False, así que un
resultado vacío se marca «needsReview» y las ofertas solo se cierran tras varias ausencias seguidas.
Cada oferta lleva la URL de su ficha oficial (no una landing) cuando existe.
"""
import re, logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .base import BaseAdapter, http_get
from ..filters import classify_job

logger = logging.getLogger(__name__)

_WS = re.compile(r"\s+")


def _soup(adapter, url):
    r = http_get(url)
    if not r:
        raise RuntimeError(f"No response from {url}")
    return BeautifulSoup(r.text, "html.parser")


class MundfishAdapter(BaseAdapter):
    """mundfish.com/en/careers: lista HTML de enlaces «Título #remote #senior» → /careers/<slug>.
    Sin ATS: se solicita por email/Telegram. La web declara «We support global remote work»
    (declaración general de la empresa; no nombra España ni el tipo de contrato)."""
    ats_type = "custom"
    uses_reliable_api = False

    LINK = re.compile(r"^/(?:[a-z]{2}/)?careers/([a-z0-9][a-z0-9-]*)/?$", re.I)
    SENIORITY_TAG = {"senior": "senior", "lead": "lead", "middle": "mid", "mid": "mid", "junior": "junior"}

    def fetch_jobs(self) -> list[dict]:
        soup = _soup(self, self.careers_url)
        page_text = _WS.sub(" ", soup.get_text(" ", strip=True)).lower()
        global_remote = "global remote work" in page_text
        seen, jobs = set(), []
        for a in soup.find_all("a", href=True):
            href = urljoin(self.careers_url, a["href"])
            m = self.LINK.match(urlparse(href).path)
            text = _WS.sub(" ", a.get_text(" ", strip=True))
            if not m or not text or text.lower() in ("read more", "more"):
                continue
            slug = m.group(1).lower()
            if slug in seen:
                continue
            seen.add(slug)
            tags = [t.lower() for t in re.findall(r"#(\w+)", text)]
            title = re.sub(r"^\s*hot\s+", "", text.split("#")[0].strip(), flags=re.I).strip()
            self.total_seen += 1
            match = classify_job(title, "")
            if not match:
                continue
            remote = "remote" in tags
            desc = ""
            if remote:
                desc = "Remote. We support global remote work." if global_remote else "Remote."
            job = self.normalize({
                "id": f"mf-{slug}", "title": title, "url": href.split("#")[0],
                "location": "Remote" if remote else "",
                "workplaceType": "remote" if remote else "unknown",
                "remoteScope": "worldwide" if (remote and global_remote) else "unknown",
                "matchType": match, "description": desc,
            })
            for t in tags:
                if t in self.SENIORITY_TAG and job["seniority"] == "unknown":
                    job["seniority"] = self.SENIORITY_TAG[t]
            from ..classify import score_job
            job["relevance"] = score_job(job)
            jobs.append(job)
        return jobs


class AxiomVfxAdapter(BaseAdapter):
    """axiomvfx.com/career: una única ficha («VFX Artist — Real-Time VFX Artist») en una web Framer.
    Evidencia oficial: «Remote, flexible engagement — full-time or contract» y sedes en Austin y
    Valencia (España). Es un estudio de servicios: la contratación laboral NO está acreditada."""
    ats_type = "custom"
    uses_reliable_api = False

    def fetch_jobs(self) -> list[dict]:
        soup = _soup(self, self.careers_url)
        text = _WS.sub(" ", soup.get_text(" ", strip=True))
        h1 = soup.find(["h1", "h2"])
        title = _WS.sub(" ", h1.get_text(" ", strip=True)) if h1 else ""
        looking = re.search(r"We['’]re looking for an? ([^.]{3,80}?) to join", text, re.I)
        if not title or not looking:
            return []                       # sin ficha reconocible: «needsReview», nunca un cierre
        self.total_seen = 1
        full_title = looking.group(1).strip() or title
        match = classify_job(full_title, text[:1500])
        if not match:
            return []
        engagement = re.search(r"Remote,[^.]{0,60}(?:full-time or contract|contract)", text, re.I)
        desc_parts = []
        if re.search(r"\bremote\b", text, re.I):
            desc_parts.append("Remote.")
        if re.search(r"across time ?zones", text, re.I):
            desc_parts.append("Able to work async across time zones.")
        if engagement:
            desc_parts.append(engagement.group(0))
        job = self.normalize({
            "id": "ax-" + re.sub(r"[^a-z0-9]+", "-", full_title.lower()).strip("-")[:40],
            "title": full_title, "url": self.careers_url, "location": "Remote",
            "workplaceType": "remote" if "remote" in text.lower() else "unknown",
            "remoteScope": "worldwide" if re.search(r"across time ?zones", text, re.I) else "unknown",
            "matchType": match, "description": " ".join(desc_parts),
        })
        return [job]
