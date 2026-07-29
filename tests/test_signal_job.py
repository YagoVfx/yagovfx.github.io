import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.scanner import build_signal_job
from scanner.sources.adzuna import check_company_has_vfx_signal


def test_signal_job_links_to_company_own_page_not_adzuna():
    company = {"name": "Example Studio", "careersUrl": "https://example.com/careers", "category": None}
    job = build_signal_job(company, now="2026-01-01T00:00:00Z")
    assert job["url"] == "https://example.com/careers"
    assert job["viaAggregator"] is False
    assert job["signalOnly"] is True
    assert job["matchType"] == "possibleMatch"
    assert "example.com" in job["url"] and "adzuna" not in job["url"]


def test_signal_check_returns_false_without_credentials():
    old_id = os.environ.pop("ADZUNA_APP_ID", None)
    old_key = os.environ.pop("ADZUNA_APP_KEY", None)
    try:
        assert check_company_has_vfx_signal("Some Studio") is False
    finally:
        if old_id is not None:
            os.environ["ADZUNA_APP_ID"] = old_id
        if old_key is not None:
            os.environ["ADZUNA_APP_KEY"] = old_key


if __name__ == "__main__":
    test_signal_job_links_to_company_own_page_not_adzuna()
    test_signal_check_returns_false_without_credentials()
    print("All tests passed.")
