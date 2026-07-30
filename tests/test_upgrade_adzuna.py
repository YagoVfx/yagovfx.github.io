import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.scanner import upgrade_adzuna_jobs_to_direct_links


def test_upgrades_job_when_cache_has_a_known_hit():
    cache = {
        "gram games": {"found": True, "ats": "greenhouse", "careersUrl": "https://job-boards.greenhouse.io/gramgamescareers", "checkedAt": 0}
    }
    jobs = [
        {"id": "az-1", "company": "Gram Games", "title": "VFX Artist", "url": "https://adzuna.es/land/ad/1", "viaAggregator": True},
    ]
    upgraded, count = upgrade_adzuna_jobs_to_direct_links(jobs, cache)
    assert count == 1
    assert upgraded[0]["url"] == "https://job-boards.greenhouse.io/gramgamescareers"
    assert upgraded[0]["viaAggregator"] is False
    assert upgraded[0]["ats"] == "greenhouse"
    # Original list must not be mutated in place.
    assert jobs[0]["viaAggregator"] is True


def test_leaves_job_unchanged_when_no_discovery_match():
    cache = {"totally unknown studio": {"found": False, "checkedAt": 9999999999}}
    jobs = [
        {"id": "az-2", "company": "Totally Unknown Studio", "title": "VFX Artist", "url": "https://adzuna.es/land/ad/2", "viaAggregator": True},
    ]
    upgraded, count = upgrade_adzuna_jobs_to_direct_links(jobs, cache)
    assert count == 0
    assert upgraded[0]["url"] == "https://adzuna.es/land/ad/2"
    assert upgraded[0]["viaAggregator"] is True


def test_only_probes_each_company_once_per_run():
    cache = {
        "gram games": {"found": True, "ats": "greenhouse", "careersUrl": "https://job-boards.greenhouse.io/gramgamescareers", "checkedAt": 0}
    }
    jobs = [
        {"id": "az-1", "company": "Gram Games", "title": "VFX Artist", "url": "x", "viaAggregator": True},
        {"id": "az-2", "company": "Gram Games", "title": "Senior VFX Artist", "url": "y", "viaAggregator": True},
    ]
    upgraded, count = upgrade_adzuna_jobs_to_direct_links(jobs, cache)
    assert count == 2
    assert all(j["viaAggregator"] is False for j in upgraded)


if __name__ == "__main__":
    test_upgrades_job_when_cache_has_a_known_hit()
    test_leaves_job_unchanged_when_no_discovery_match()
    test_only_probes_each_company_once_per_run()
    print("All tests passed.")
