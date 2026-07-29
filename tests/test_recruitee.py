import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.adapters.recruitee import build_recruitee_api_url


def test_build_from_subdomain():
    assert build_recruitee_api_url("https://examplestudio.recruitee.com") == "https://examplestudio.recruitee.com/api/offers/"
    assert build_recruitee_api_url("https://examplestudio.recruitee.com/") == "https://examplestudio.recruitee.com/api/offers/"


def test_build_from_custom_domain():
    # Recruitee also supports the same /api/offers/ path on a company's
    # own custom domain when they've set one up.
    assert build_recruitee_api_url("https://careers.examplestudio.com") == "https://careers.examplestudio.com/api/offers/"


def test_build_returns_none_for_empty_input():
    assert build_recruitee_api_url("") is None


if __name__ == "__main__":
    test_build_from_subdomain()
    test_build_from_custom_domain()
    test_build_returns_none_for_empty_input()
    print("All tests passed.")
