import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pytest
from scanner.scanner import resolve_ats
from scanner.adapters.lever import LeverAdapter, extract_lever_company, lever_api_base
from scanner.adapters.greenhouse import GreenhouseAdapter
import scanner.adapters.lever as lever_mod


def test_explicit_custom_no_longer_overrides_a_known_ats_url():
    assert resolve_ats({"type": "custom", "careersUrl": "https://job-boards.greenhouse.io/guerrilla-games"}) == "greenhouse"
    assert resolve_ats({"type": "custom", "careersUrl": "https://jobs.eu.lever.co/frontier"}) == "lever"
    assert resolve_ats({"careersUrl": "https://jobs.lever.co/x"}) == "lever"

def test_explicit_non_custom_type_and_true_custom_are_respected():
    assert resolve_ats({"type": "workday", "careersUrl": "https://x.test"}) == "workday"
    assert resolve_ats({"type": "custom", "careersUrl": "https://www.epicgames.com/site/careers"}) == "custom"

def test_lever_eu_board_uses_eu_api_host():
    assert extract_lever_company("https://jobs.eu.lever.co/frontier") == "frontier"
    assert lever_api_base("https://jobs.eu.lever.co/frontier") == "https://api.eu.lever.co"
    assert lever_api_base("https://jobs.lever.co/frontier") == "https://api.lever.co"

class _R:
    def __init__(self, data): self._d = data
    def json(self): return self._d

def test_lever_eu_calls_eu_endpoint_and_parses(monkeypatch):
    seen = []
    monkeypatch.setattr(lever_mod, "http_get", lambda url, *a, **k: (seen.append(url), _R([{"id": "abc-123", "text": "Senior VFX Artist", "hostedUrl": "https://jobs.eu.lever.co/frontier/1", "categories": {"location": "Remote - UK"}, "descriptionPlain": "Niagara"}]))[1])
    jobs = LeverAdapter({"name": "Frontier", "careersUrl": "https://jobs.eu.lever.co/frontier"}).fetch_jobs()
    assert seen == ["https://api.eu.lever.co/v0/postings/frontier?mode=json"]
    assert len(jobs) == 1 and jobs[0]["sourceKind"] == "ats" and jobs[0]["verification"] == "verified"

@pytest.mark.parametrize("cls,url", [(LeverAdapter, "https://example.test/careers"), (GreenhouseAdapter, "https://example.test/careers")])
def test_unparseable_url_is_an_error_not_a_silent_zero(cls, url):
    with pytest.raises(RuntimeError):
        cls({"name": "X", "careersUrl": url}).fetch_jobs()
