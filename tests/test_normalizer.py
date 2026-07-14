import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.normalizer import generate_job_id, preserve_first_seen


def test_generate_job_id_is_stable():
    id1 = generate_job_id("gh", "https://boards.greenhouse.io/example/jobs/12345")
    id2 = generate_job_id("gh", "https://boards.greenhouse.io/example/jobs/12345")
    assert id1 == id2


def test_generate_job_id_differs_per_url():
    id1 = generate_job_id("tt", "https://cigames.teamtailor.com/jobs/1-vfx-artist")
    id2 = generate_job_id("tt", "https://cigames.teamtailor.com/jobs/2-vfx-artist")
    assert id1 != id2


def test_preserve_first_seen_keeps_old_date_for_existing_job():
    existing = {"gh-123": {"id": "gh-123", "firstSeen": "2026-01-01T00:00:00Z"}}
    job = {"id": "gh-123", "title": "Senior VFX Artist"}
    result = preserve_first_seen(existing, job, now="2026-07-14T00:00:00Z")
    assert result["firstSeen"] == "2026-01-01T00:00:00Z"
    assert result["lastSeen"] == "2026-07-14T00:00:00Z"


def test_preserve_first_seen_sets_new_date_for_new_job():
    existing = {}
    job = {"id": "gh-999", "title": "VFX Artist"}
    result = preserve_first_seen(existing, job, now="2026-07-14T00:00:00Z")
    assert result["firstSeen"] == "2026-07-14T00:00:00Z"
    assert result["lastSeen"] == "2026-07-14T00:00:00Z"


if __name__ == "__main__":
    test_generate_job_id_is_stable()
    test_generate_job_id_differs_per_url()
    test_preserve_first_seen_keeps_old_date_for_existing_job()
    test_preserve_first_seen_sets_new_date_for_new_job()
    print("All tests passed.")
