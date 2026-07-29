import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.scanner import build_signal_job
from scanner.sources.adzuna import company_names_match, find_signal_matches


def test_signal_job_links_to_company_own_page_not_adzuna():
    company = {"name": "Example Studio", "careersUrl": "https://example.com/careers", "category": None}
    job = build_signal_job(company, now="2026-01-01T00:00:00Z")
    assert job["url"] == "https://example.com/careers"
    assert job["viaAggregator"] is False
    assert job["signalOnly"] is True
    assert job["matchType"] == "possibleMatch"
    assert "adzuna" not in job["url"]


def test_company_names_match_handles_legal_name_variance():
    # Exact / substring cases
    assert company_names_match("EA", "EA Vancouver")
    assert company_names_match("Embark Studios", "Embark")
    # Near-miss spelling ("Project" vs "Projekt") should still fuzzy-match
    assert company_names_match("CD Project", "CD Projekt Red S.A.")
    # Clearly unrelated names should not match
    assert not company_names_match("Lighthouse Games", "Ubisoft Montreal")


def test_find_signal_matches_reuses_broad_results_no_extra_query():
    adzuna_jobs = [
        {"id": "az-1", "company": "Rebellion Developments", "title": "VFX Artist"},
        {"id": "az-2", "company": "Some Unrelated Co", "title": "VFX Artist"},
    ]
    companies_to_check = [
        {"name": "Rebellion", "careersUrl": "https://careers.rebellion.com"},
        {"name": "Jagex", "careersUrl": "https://www.jagex.com"},
    ]
    signals, matched_ids = find_signal_matches(adzuna_jobs, companies_to_check)
    assert signals.get("Rebellion") is True
    assert "Jagex" not in signals
    assert matched_ids == ["az-1"]


if __name__ == "__main__":
    test_signal_job_links_to_company_own_page_not_adzuna()
    test_company_names_match_handles_legal_name_variance()
    test_find_signal_matches_reuses_broad_results_no_extra_query()
    print("All tests passed.")
