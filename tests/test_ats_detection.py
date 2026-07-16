import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.companies import (
    detect_ats,
    normalize_url,
    dedupe_key,
    guess_name_from_url,
    dedupe_companies,
    parse_bulk_urls,
)


def test_detect_ats_greenhouse():
    assert detect_ats("https://boards.greenhouse.io/riotgames") == "greenhouse"
    assert detect_ats("https://job-boards.greenhouse.io/example") == "greenhouse"


def test_detect_ats_lever():
    assert detect_ats("https://jobs.lever.co/naughtydog") == "lever"


def test_detect_ats_teamtailor():
    assert detect_ats("https://cigames.teamtailor.com/") == "teamtailor"
    assert detect_ats("https://cigames.teamtailor.com/jobs") == "teamtailor"


def test_detect_ats_workday():
    assert detect_ats("https://activision.wd1.myworkdayjobs.com/Blizzard_External_Careers") == "workday"
    assert detect_ats("https://ea.wd1.myworkdayjobs.com/en-US/Electronic_Arts") == "workday"


def test_detect_ats_custom_fallback():
    assert detect_ats("https://example-studio.com/careers") == "custom"
    assert detect_ats("") == "custom"


def test_normalize_url_preserves_trailing_slash():
    # normalize_url must NOT touch a trailing slash — some sites genuinely
    # need it to work (e.g. https://x.com/careers/ errors without it).
    assert normalize_url("https://lighthousegames.com/careers/") == "https://lighthousegames.com/careers/"
    assert normalize_url("https://cigames.teamtailor.com/") == "https://cigames.teamtailor.com/"
    assert normalize_url("cigames.teamtailor.com") == "https://cigames.teamtailor.com"


def test_dedupe_key_ignores_trailing_slash():
    # dedupe_key (comparison-only) should treat these as equal, without
    # mutating what actually gets saved.
    assert dedupe_key("https://x.com/careers") == dedupe_key("https://x.com/careers/")


def test_guess_name_from_url():
    assert guess_name_from_url("https://boards.greenhouse.io/riotgames") == "Riotgames"
    assert guess_name_from_url("https://cigames.teamtailor.com/") == "Cigames"


def test_dedupe_companies_by_normalized_url():
    companies = [
        {"name": "CI Games", "careersUrl": "https://cigames.teamtailor.com/", "type": "teamtailor"},
        {"name": "CI Games (dup)", "careersUrl": "https://cigames.teamtailor.com", "type": "teamtailor"},
        {"name": "Riot Games", "careersUrl": "https://boards.greenhouse.io/riotgames", "type": "greenhouse"},
    ]
    deduped = dedupe_companies(companies)
    assert len(deduped) == 2
    assert deduped[0]["name"] == "CI Games"  # first occurrence wins


def test_parse_bulk_urls_end_to_end():
    text = """
    https://boards.greenhouse.io/example
    https://jobs.lever.co/example
    https://boards.greenhouse.io/example
    """
    parsed = parse_bulk_urls(text)
    assert len(parsed) == 2
    types = {c["type"] for c in parsed}
    assert types == {"greenhouse", "lever"}


if __name__ == "__main__":
    test_detect_ats_greenhouse()
    test_detect_ats_lever()
    test_detect_ats_teamtailor()
    test_detect_ats_workday()
    test_detect_ats_custom_fallback()
    test_normalize_url_preserves_trailing_slash()
    test_dedupe_key_ignores_trailing_slash()
    test_guess_name_from_url()
    test_dedupe_companies_by_normalized_url()
    test_parse_bulk_urls_end_to_end()
    print("All tests passed.")
