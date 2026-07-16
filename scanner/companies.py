"""
Helpers for managing the companies list: ATS detection from URL,
URL normalization, name guessing and de-duplication.

Kept separate from scanner.py so it can be unit-tested in isolation
and reused by any future tooling (e.g. a CLI importer).
"""
import re
from urllib.parse import urlparse


def detect_ats(url: str) -> str:
    """Detect the ATS type from a careers URL. Falls back to 'custom'."""
    if not url:
        return "custom"
    if re.search(r"greenhouse\.io", url, re.IGNORECASE):
        return "greenhouse"
    if re.search(r"lever\.co", url, re.IGNORECASE):
        return "lever"
    if re.search(r"teamtailor\.com", url, re.IGNORECASE):
        return "teamtailor"
    if re.search(r"myworkdayjobs\.com", url, re.IGNORECASE):
        return "workday"
    if re.search(r"workable\.com", url, re.IGNORECASE):
        return "workable"
    return "custom"


def normalize_url(url: str) -> str:
    """Trim whitespace and ensure a scheme. Does NOT touch a trailing
    slash — some sites genuinely need it (e.g. a path that 404s or errors
    without the final slash), so whatever is entered is preserved as-is.
    For de-duplication comparisons, use dedupe_key() instead; don't use
    this function's output as a comparison key.
    """
    if not url:
        return ""
    url = url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    return url


def dedupe_key(url: str) -> str:
    """Comparison-only key: same as normalize_url() but also strips a
    trailing slash and lowercases, so 'x.com/careers' and 'x.com/careers/'
    are treated as the same company for de-dup purposes — WITHOUT mutating
    the actual URL that gets saved/fetched.
    """
    return normalize_url(url).rstrip("/").lower()


def guess_name_from_url(url: str) -> str:
    """Best-effort company name guess from the URL's host or path slug."""
    normalized = normalize_url(url)
    if not normalized:
        return ""
    parsed = urlparse(normalized)
    host = re.sub(r"^www\.", "", parsed.netloc)

    slug = ""
    if "greenhouse.io" in host or "lever.co" in host:
        parts = [p for p in parsed.path.split("/") if p]
        slug = parts[0] if parts else ""
    elif "teamtailor.com" in host:
        slug = host.split(".")[0]
    elif "myworkdayjobs.com" in host:
        # e.g. activision.wd1.myworkdayjobs.com/Blizzard_External_Careers -> "Blizzard External Careers"
        parts = [p for p in parsed.path.split("/") if p and not re.match(r"^[a-z]{2}-[A-Z]{2}$", p)]
        slug = parts[0] if parts else host.split(".")[0]
        slug = re.sub(r"_?external_?careers?", "", slug, flags=re.IGNORECASE).strip("_ ") or slug
    else:
        slug = host.split(".")[0] if host else ""

    if not slug:
        return host
    return slug.replace("-", " ").replace("_", " ").title()


def dedupe_companies(companies: list[dict]) -> list[dict]:
    """Remove duplicate companies by normalized careersUrl, keeping the
    first occurrence (so manual edits earlier in the list win)."""
    seen = set()
    out = []
    for company in companies:
        key = dedupe_key(company.get("careersUrl", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(company)
    return out


def parse_bulk_urls(text: str) -> list[dict]:
    """Parse a newline-separated block of URLs into normalized,
    de-duplicated company dicts with auto-detected ATS and a guessed name.
    Mirrors the behaviour of the admin panel's bulk-import feature (JS),
    so companies.json produced by either path has the same shape.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    companies = []
    for line in lines:
        url = normalize_url(line)
        if not url:
            continue
        companies.append({
            "name": guess_name_from_url(url),
            "careersUrl": url,
            "type": detect_ats(url),
        })
    return dedupe_companies(companies)
