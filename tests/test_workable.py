import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.adapters.workable import extract_workable_account, extract_jobs_portal_company_id
from scanner.adapters.workable import WorkableAdapter
from unittest.mock import Mock, patch
import pytest


def test_global_search_is_rejected_instead_of_attributing_other_companies_jobs():
    adapter = WorkableAdapter({"name": "Lighthouse", "careersUrl": "https://jobs.workable.com/company/123/jobs-at-lighthouse"})
    with patch("requests.get") as get:
        with pytest.raises(RuntimeError, match="company identity"):
            adapter.fetch_jobs()
        get.assert_not_called()


def test_official_widget_deduplicates_and_keeps_all_locations_and_date():
    response = Mock()
    template = {"title": "Senior VFX Artist", "shortcode": "ABC123", "description": "<p>Full-time permanent employee</p>",
                "url": "https://apply.workable.com/j/ABC123", "published_on": "2026-10-23"}
    response.json.return_value = {"jobs": [dict(template, city="Oxford", country="United Kingdom"),
                                         dict(template, city="Warwick", country="United Kingdom")]}
    with patch("scanner.adapters.workable.http_get", return_value=response) as get:
        jobs = WorkableAdapter({"name": "Rebellion", "careersUrl": "https://apply.workable.com/rebellion/"}).fetch_jobs()
    assert "accounts/rebellion" in get.call_args.args[0]
    assert len(jobs) == 1
    assert "Oxford" in jobs[0]["location"] and "Warwick" in jobs[0]["location"]
    assert jobs[0]["postedDate"] == "2026-10-23"
    assert jobs[0]["sourceKind"] == "ats" and jobs[0]["verification"] == "verified"


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


def test_extract_jobs_portal_company_id():
    url = "https://jobs.workable.com/company/9NdGchEYkMTDejHGaa9eHJ/jobs-at-lighthouse-games"
    assert extract_jobs_portal_company_id(url) == "9NdGchEYkMTDejHGaa9eHJ"
    assert extract_jobs_portal_company_id("https://apply.workable.com/lighthousegames/") is None


if __name__ == "__main__":
    test_extract_from_apply_workable_url()
    test_extract_from_legacy_subdomain()
    test_extract_returns_none_for_custom_domain()
    test_extract_jobs_portal_company_id()
    print("All tests passed.")
