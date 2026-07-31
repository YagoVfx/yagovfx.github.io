import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.scanner import compute_jobs_by_ats


def test_counts_per_adapter():
    jobs = [
        {"ats": "greenhouse"},
        {"ats": "greenhouse"},
        {"ats": "lever"},
        {"ats": "adzuna"},
        {"ats": "adzuna-signal"},
    ]
    counts = compute_jobs_by_ats(jobs)
    assert counts == {"greenhouse": 2, "lever": 1, "adzuna": 1, "adzuna-signal": 1}


def test_upgraded_adzuna_job_counts_under_its_real_ats():
    # After upgrade_adzuna_jobs_to_direct_links rewrites "ats" to the
    # discovered board type, it should count there, not under "adzuna".
    jobs = [{"ats": "greenhouse"}, {"ats": "adzuna"}]
    counts = compute_jobs_by_ats(jobs)
    assert counts["greenhouse"] == 1
    assert counts["adzuna"] == 1


def test_empty_list():
    assert compute_jobs_by_ats([]) == {}


if __name__ == "__main__":
    test_counts_per_adapter()
    test_upgraded_adzuna_job_counts_under_its_real_ats()
    test_empty_list()
    print("All tests passed.")
