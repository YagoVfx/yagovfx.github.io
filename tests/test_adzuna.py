import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.sources.adzuna import fetch_adzuna_jobs


def test_skips_gracefully_without_credentials():
    # Make sure we don't accidentally have real creds in this environment
    # affecting the test.
    old_id = os.environ.pop("ADZUNA_APP_ID", None)
    old_key = os.environ.pop("ADZUNA_APP_KEY", None)
    try:
        jobs, status = fetch_adzuna_jobs()
        assert jobs == []
        assert status["status"] == "skipped"
    finally:
        if old_id is not None:
            os.environ["ADZUNA_APP_ID"] = old_id
        if old_key is not None:
            os.environ["ADZUNA_APP_KEY"] = old_key


if __name__ == "__main__":
    test_skips_gracefully_without_credentials()
    print("All tests passed.")
