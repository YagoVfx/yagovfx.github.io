import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.auto_discover import _slugify_candidates, discover_direct_source


def test_slugify_candidates_basic():
    candidates = _slugify_candidates("Gram Games")
    assert "gramgames" in candidates
    assert "gram-games" in candidates
    assert "gram" in candidates  # first word alone


def test_slugify_candidates_adds_games_suffix_when_missing():
    candidates = _slugify_candidates("Asobo Studio")
    assert "asobostudio" in candidates
    assert "asobostudiogames" in candidates


def test_slugify_candidates_empty_input():
    assert _slugify_candidates("") == []
    assert _slugify_candidates(None) == []


def test_discover_uses_cached_hit_without_reprobing():
    cache = {"known studio": {"found": True, "ats": "greenhouse", "careersUrl": "https://job-boards.greenhouse.io/knownstudio", "checkedAt": 0}}
    result = discover_direct_source("Known Studio", cache=cache)
    assert result == {"ats": "greenhouse", "careersUrl": "https://job-boards.greenhouse.io/knownstudio"}


def test_discover_skips_reprobing_recent_miss():
    import time
    cache = {"tiny indie co": {"found": False, "checkedAt": time.time()}}
    result = discover_direct_source("Tiny Indie Co", cache=cache)
    assert result is None


if __name__ == "__main__":
    test_slugify_candidates_basic()
    test_slugify_candidates_adds_games_suffix_when_missing()
    test_slugify_candidates_empty_input()
    test_discover_uses_cached_hit_without_reprobing()
    test_discover_skips_reprobing_recent_miss()
    print("All tests passed.")
