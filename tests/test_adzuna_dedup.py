import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.scanner import dedupe_adzuna_against_direct_matches


def test_drops_adzuna_job_already_found_directly():
    direct_jobs = {
        "gh-1": {"id": "gh-1", "company": "Embark Studios", "title": "Senior VFX Artist", "viaAggregator": False},
    }
    adzuna_jobs = [
        {"id": "az-1", "company": "Embark Studios", "title": "Senior VFX Artist"},
        {"id": "az-2", "company": "Some Other Studio", "title": "VFX Artist"},
    ]
    result = dedupe_adzuna_against_direct_matches(adzuna_jobs, direct_jobs)
    assert len(result) == 1
    assert result[0]["id"] == "az-2"


def test_case_and_whitespace_insensitive_matching():
    direct_jobs = {
        "gh-1": {"id": "gh-1", "company": "  Embark Studios  ", "title": "SENIOR VFX ARTIST", "viaAggregator": False},
    }
    adzuna_jobs = [
        {"id": "az-1", "company": "embark studios", "title": "senior vfx artist"},
    ]
    result = dedupe_adzuna_against_direct_matches(adzuna_jobs, direct_jobs)
    assert result == []


def test_does_not_drop_against_another_aggregator_job():
    # A direct-adapter match is required to win; an existing job that
    # itself came via an aggregator shouldn't suppress a new Adzuna result.
    direct_jobs = {
        "az-old": {"id": "az-old", "company": "Embark Studios", "title": "Senior VFX Artist", "viaAggregator": True},
    }
    adzuna_jobs = [
        {"id": "az-new", "company": "Embark Studios", "title": "Senior VFX Artist"},
    ]
    result = dedupe_adzuna_against_direct_matches(adzuna_jobs, direct_jobs)
    assert len(result) == 1


if __name__ == "__main__":
    test_drops_adzuna_job_already_found_directly()
    test_case_and_whitespace_insensitive_matching()
    test_does_not_drop_against_another_aggregator_job()
    print("All tests passed.")
