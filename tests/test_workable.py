import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.adapters.workable import extract_workable_account


def test_extract_from_apply_workable_url():
    assert extract_workable_account("https://apply.workable.com/lighthousegames/") == "lighthousegames"
    assert extract_workable_account("https://apply.workable.com/lighthousegames") == "lighthousegames"


def test_extract_from_legacy_subdomain():
    assert extract_workable_account("https://lighthousegames.workable.com/") == "lighthousegames"


def test_extract_returns_none_for_custom_domain():
    # A company's own domain with Workable embedded via JS can't be resolved
    # to an account slug from the URL alone.
    assert extract_workable_account("https://lighthousegames.com/careers/") is None
    assert extract_workable_account("") is None


if __name__ == "__main__":
    test_extract_from_apply_workable_url()
    test_extract_from_legacy_subdomain()
    test_extract_returns_none_for_custom_domain()
    print("All tests passed.")
