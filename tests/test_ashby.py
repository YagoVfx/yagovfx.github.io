import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.adapters.ashby import extract_ashby_board


def test_extract_from_jobs_ashbyhq_url():
    assert extract_ashby_board("https://jobs.ashbyhq.com/example-studio") == "example-studio"
    assert extract_ashby_board("https://jobs.ashbyhq.com/example-studio/") == "example-studio"


def test_extract_from_api_url():
    assert extract_ashby_board("https://api.ashbyhq.com/posting-api/job-board/example-studio") == "example-studio"


def test_extract_returns_none_for_unrelated_url():
    assert extract_ashby_board("https://boards.greenhouse.io/example") is None
    assert extract_ashby_board("") is None


if __name__ == "__main__":
    test_extract_from_jobs_ashbyhq_url()
    test_extract_from_api_url()
    test_extract_returns_none_for_unrelated_url()
    print("All tests passed.")
