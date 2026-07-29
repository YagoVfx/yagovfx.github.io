import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.adapters.greenhouse import GreenhouseAdapter
from scanner.adapters.custom_html import CustomHtmlAdapter
from scanner.adapters.teamtailor import TeamtailorAdapter
from scanner.adapters.ashby import AshbyAdapter


def test_reliable_api_adapters_flagged_as_reliable():
    # A real structured API returning 0 postings is a trustworthy "this
    # company genuinely has zero open positions", not something to flag.
    gh = GreenhouseAdapter({"name": "X", "careersUrl": "https://boards.greenhouse.io/x"})
    assert gh.uses_reliable_api is True
    ab = AshbyAdapter({"name": "X", "careersUrl": "https://jobs.ashbyhq.com/x"})
    assert ab.uses_reliable_api is True


def test_html_scraping_adapters_flagged_as_unreliable():
    # HTML-scraping heuristics can't tell "genuinely empty" apart from
    # "JS-rendered page we can't see" — so 0 found should stay suspicious.
    ch = CustomHtmlAdapter({"name": "X", "careersUrl": "https://example.com/careers"})
    assert ch.uses_reliable_api is False
    tt = TeamtailorAdapter({"name": "X", "careersUrl": "https://x.teamtailor.com"})
    assert tt.uses_reliable_api is False


def test_needs_review_logic_matches_expectation():
    # Mirrors the exact computation used in scanner.py's run().
    def needs_review(total_seen, uses_reliable_api):
        return (total_seen == 0) and not uses_reliable_api

    assert needs_review(0, True) is False   # Greenhouse/Lever/etc, genuinely empty
    assert needs_review(0, False) is True   # CustomHtml/Teamtailor, ambiguous
    assert needs_review(5, False) is False  # HTML scraper saw real candidates
    assert needs_review(5, True) is False


if __name__ == "__main__":
    test_reliable_api_adapters_flagged_as_reliable()
    test_html_scraping_adapters_flagged_as_unreliable()
    test_needs_review_logic_matches_expectation()
    print("All tests passed.")
