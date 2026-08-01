import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.adapters.smartrecruiters import extract_smartrecruiters_company


def test_extract_from_careers_url():
    assert extract_smartrecruiters_company("https://careers.smartrecruiters.com/ExampleStudio") == "ExampleStudio"


def test_extract_from_jobs_url():
    assert extract_smartrecruiters_company("https://jobs.smartrecruiters.com/ExampleStudio/12345-vfx-artist") == "ExampleStudio"


def test_extract_from_raw_api_url():
    # Regression test: this URL form used to incorrectly extract "v1" as
    # the company identifier instead of the real one.
    assert extract_smartrecruiters_company("https://api.smartrecruiters.com/v1/companies/CDPROJEKTRED/postings") == "CDPROJEKTRED"


def test_extract_returns_none_for_unrelated_url():
    assert extract_smartrecruiters_company("https://boards.greenhouse.io/example") is None
    assert extract_smartrecruiters_company("") is None


if __name__ == "__main__":
    test_extract_from_careers_url()
    test_extract_from_jobs_url()
    test_extract_from_raw_api_url()
    test_extract_returns_none_for_unrelated_url()
    print("All tests passed.")
