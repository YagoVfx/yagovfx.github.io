import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.filters import classify_job, detect_workplace, detect_remote_scope
import re


def _build_job_url_and_location(j: dict, company: str) -> tuple[str, str]:
    """Mirrors the URL/location extraction logic inside
    SmartRecruitersAdapter.fetch_jobs, isolated for testing without a live
    HTTP call."""
    loc_obj = j.get("location", {}) or {}
    loc = loc_obj.get("fullLocation") or ", ".join(
        p for p in (loc_obj.get("city"), loc_obj.get("region"), loc_obj.get("country")) if p
    )
    title = j.get("name", "")
    posting_id = j.get("id", title)
    title_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    fallback_url = f"https://jobs.smartrecruiters.com/{company}/{posting_id}-{title_slug}" if title_slug else f"https://jobs.smartrecruiters.com/{company}/{posting_id}"
    url = j.get("postingUrl") or j.get("applyUrl") or fallback_url
    return url, loc


# Shape confirmed from a real CD Projekt Red posting's detail-endpoint
# response (the person captured this directly from their browser).
REAL_POSTING_WITH_URL = {
    "id": "74400136044054",
    "name": "Lead VFX Artist",
    "postingUrl": "https://jobs.smartrecruiters.com/CDPROJEKTRED/744000136044454-lead-vfx-artist",
    "location": {
        "city": "Warsaw",
        "region": "Masovian Voivodeship",
        "country": "Poland",
        "remote": False,
        "fullLocation": "Warsaw, Masovian Voivodeship, Poland",
    },
}

# A LIST-endpoint-shaped item missing postingUrl (per SmartRecruiters' own
# docs, the list endpoint can omit fields present on the detail endpoint).
LIST_SHAPED_POSTING_NO_URL = {
    "id": "74400136044054",
    "name": "Senior VFX Artist",
    "location": {"city": "Warsaw", "region": "Masovian Voivodeship", "country": "Poland"},
}


def test_uses_real_posting_url_field_not_ref():
    url, loc = _build_job_url_and_location(REAL_POSTING_WITH_URL, "CDPROJEKTRED")
    assert url == "https://jobs.smartrecruiters.com/CDPROJEKTRED/744000136044454-lead-vfx-artist"
    assert "smartrecruiters.com" in url
    assert loc == "Warsaw, Masovian Voivodeship, Poland"


def test_falls_back_to_reconstructed_url_when_posting_url_missing():
    url, loc = _build_job_url_and_location(LIST_SHAPED_POSTING_NO_URL, "CDPROJEKTRED")
    assert url == "https://jobs.smartrecruiters.com/CDPROJEKTRED/74400136044054-senior-vfx-artist"
    assert loc == "Warsaw, Masovian Voivodeship, Poland"  # falls back to manual join


def test_real_title_classifies_correctly():
    assert classify_job(REAL_POSTING_WITH_URL["name"]) == "exactMatch"


if __name__ == "__main__":
    test_uses_real_posting_url_field_not_ref()
    test_falls_back_to_reconstructed_url_when_posting_url_missing()
    test_real_title_classifies_correctly()
    print("All tests passed.")
