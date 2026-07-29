import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.adapters.personio import extract_personio_subdomain


def test_extract_from_de_url():
    assert extract_personio_subdomain("https://examplestudio.jobs.personio.de/") == "examplestudio"


def test_extract_from_com_url():
    assert extract_personio_subdomain("https://examplestudio.jobs.personio.com/") == "examplestudio"


def test_extract_returns_none_for_unrelated_url():
    assert extract_personio_subdomain("https://boards.greenhouse.io/example") is None
    assert extract_personio_subdomain("") is None


if __name__ == "__main__":
    test_extract_from_de_url()
    test_extract_from_com_url()
    test_extract_returns_none_for_unrelated_url()
    print("All tests passed.")
