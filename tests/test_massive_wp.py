import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
import re
from scanner.filters import classify_job

# Real HTML fragments captured from massive.se's own AJAX response
# (POST https://www.massive.se/wp-content/themes/massive/inc/ajax.php,
# action=get_jobs&paged=2), used here to validate the parsing logic
# without needing live network access in the test suite.
REAL_FRAGMENT_VFX = (
    '\n<a href="https://www.massive.se/job/senior-vfx-artist-744000131860128/" '
    'title="Senior VFX Artist" class="row no-gutters jobs__row pr js-jobs-row">\n'
    '\t<div class="col-12 col-sm-4 jobs__column">\n'
    '\t\t<div class="jobs__cell-inner" data-sort="title">\n'
    '\t\t\t<h4 class="mb-0 jobs__title">Senior VFX Artist</h4>\n'
    '\t\t\t\t\t\t\t<div class="d-xs-block d-sm-none">Art, Malmö, '
    "Tom Clancy&#039;s The Division 2: Survivors</div>\n"
    "\t\t\t\t\t</div>\n\t</div>\n</a>\n"
)

REAL_FRAGMENT_NON_VFX = (
    '\n<a href="https://www.massive.se/job/senior-tools-programmer-744000127003896/" '
    'title="Senior Tools Programmer" class="row no-gutters jobs__row pr js-jobs-row">\n'
    '\t<div class="col-12 col-sm-4 jobs__column">\n'
    '\t\t<div class="jobs__cell-inner" data-sort="title">\n'
    '\t\t\t<h4 class="mb-0 jobs__title">Senior Tools Programmer</h4>\n'
    '\t\t\t\t\t\t\t<div class="d-xs-block d-sm-none">Software Development, Malmö, '
    "Tom Clancy&#039;s The Division 3</div>\n"
    "\t\t\t\t\t</div>\n\t</div>\n</a>\n"
)


def _parse_fragment(fragment: str):
    """Mirrors the parsing logic in MassiveWPAdapter.fetch_jobs, isolated
    here so it's testable without a live HTTP call."""
    soup = BeautifulSoup(fragment, "lxml")
    a = soup.find("a")
    url = a.get("href", "")
    title_tag = a.find("h4")
    title = (title_tag.get_text(strip=True) if title_tag else a.get("title", "")) or ""
    meta_div = soup.find("div", class_=re.compile(r"d-xs-block"))
    meta_text = meta_div.get_text(" ", strip=True) if meta_div else ""
    return title, url, meta_text


def test_extracts_title_and_url_from_real_fragment():
    title, url, meta = _parse_fragment(REAL_FRAGMENT_VFX)
    assert title == "Senior VFX Artist"
    assert url == "https://www.massive.se/job/senior-vfx-artist-744000131860128/"
    assert "Malmö" in meta


def test_vfx_fragment_classifies_as_exact_match():
    title, url, meta = _parse_fragment(REAL_FRAGMENT_VFX)
    assert classify_job(title, meta) == "exactMatch"


def test_non_vfx_fragment_does_not_match():
    title, url, meta = _parse_fragment(REAL_FRAGMENT_NON_VFX)
    assert classify_job(title, meta) is None


if __name__ == "__main__":
    test_extracts_title_and_url_from_real_fragment()
    test_vfx_fragment_classifies_as_exact_match()
    test_non_vfx_fragment_does_not_match()
    print("All tests passed.")
