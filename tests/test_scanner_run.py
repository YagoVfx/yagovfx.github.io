"""Ejecución completa de scanner.run() con adaptadores y Adzuna simulados:
demuestra que el pipeline sigue funcionando de extremo a extremo SIN red."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scanner import scanner as sc
from scanner.adapters.base import BaseAdapter

NOW1, NOW2 = "2026-10-01T06:00:00Z", "2026-10-02T06:00:00Z"

def fake_adapter(result):
    class A(BaseAdapter):
        ats_type = "greenhouse"
        def fetch_jobs(self):
            if isinstance(result.get(self.company), Exception):
                raise result[self.company]
            return [self.normalize(j) for j in result.get(self.company, [])]
    return A

def gh(i, title="Senior VFX Artist", loc="Remote - Spain"):
    return {"id": f"gh-{i}", "title": title, "url": f"https://boards.greenhouse.io/x/jobs/{i}", "location": loc,
            "workplaceType": "remote", "remoteScope": "Spain", "matchType": "exactMatch"}

def az_fetcher(jobs, status="ok", truncated=False):
    def f():
        return list(jobs), {"source": "Adzuna", "company": "(Adzuna)", "status": status, "jobsFound": len(jobs), "truncated": truncated}
    return f

def setup(tmp_path, companies):
    (tmp_path / "companies.json").write_text(json.dumps(companies))
    return tmp_path

def go(tmp_path, results, az=None, now=NOW1):
    return sc.run(now=now, data_dir=tmp_path, adapters={"greenhouse": fake_adapter(results)},
                  adzuna_fetcher=az or az_fetcher([]), discover_cache_loader=lambda: {}, discover_cache_saver=lambda c: None)

COS = [{"name": "A", "careersUrl": "https://boards.greenhouse.io/a", "type": "greenhouse"},
       {"name": "2K", "careersUrl": "https://boards.greenhouse.io/2k", "type": "greenhouse"}]

def test_full_run_writes_v2_outputs(tmp_path):
    setup(tmp_path, COS)
    out, statuses, report = go(tmp_path, {"A": [gh(1)], "2K": [gh(2)]})
    data = json.loads((tmp_path / "jobs.json").read_text())
    assert data["schemaVersion"] == 2 and data["totalVfxJobs"] == 2
    j = data["jobs"][0]
    for k in ("spainEligibility", "contractType", "relevance", "compatibility", "verification", "sourceKind"):
        assert k in j
    assert j["verification"] == "verified" and j["sourceKind"] == "ats"
    assert (tmp_path / "scanner-status.json").exists() and (tmp_path / "scanner-report.json").exists()
    assert report["summary"]["officialJobs"] == 2 and report["summary"]["aggregatorShare"] == 0

def test_data01_failed_ats_keeps_old_jobs(tmp_path):
    setup(tmp_path, COS)
    go(tmp_path, {"A": [gh(1)], "2K": [gh(2)]})
    out, statuses, _ = go(tmp_path, {"A": [gh(1)], "2K": RuntimeError("No response from https://2k.com/careers")}, now=NOW2)
    byid = {j["id"]: j for j in out["jobs"]}
    assert byid["gh-2"]["status"] == "active"                       # NO se cierra por fallo de su fuente
    st = {s["company"]: s for s in statuses}
    assert st["2K"]["status"] == "error" and st["2K"]["errorKind"] == "timeout"
    assert st["2K"]["consecutiveFailures"] == 1 and st["2K"]["lastSuccess"] == NOW1

def test_successful_scan_closes_vanished_job_and_keeps_lastseen(tmp_path):
    setup(tmp_path, COS)
    go(tmp_path, {"A": [gh(1)], "2K": [gh(2)]})
    out, _, _ = go(tmp_path, {"A": [], "2K": [gh(2)]}, now=NOW2)
    j = {x["id"]: x for x in out["jobs"]}["gh-1"]
    assert j["status"] == "closed" and j["closedAt"] == NOW2 and j["lastSeen"] == NOW1

def test_data02_adzuna_duplicate_is_merged(tmp_path):
    setup(tmp_path, COS)
    az = az_fetcher([{"id": "az-9", "company": "A", "title": "Senior VFX Artist", "url": "https://adzuna/9", "ats": "adzuna",
                      "viaAggregator": True, "sourceKind": "aggregator", "status": "active", "matchType": "exactMatch"}])
    out, _, report = go(tmp_path, {"A": [gh(1)], "2K": []}, az=az)
    ids = [j["id"] for j in out["jobs"]]
    assert "az-9" not in ids and report["summary"]["duplicatesMerged"] == 1
    assert {x["id"]: x for x in out["jobs"]}["gh-1"]["alsoSeenIn"] == ["adzuna"]

def test_adzuna_job_keeps_its_own_url_and_stays_unverified(tmp_path):
    setup(tmp_path, COS)
    az = az_fetcher([{"id": "az-5", "company": "Zeta", "title": "VFX Artist", "url": "https://adzuna/5", "ats": "adzuna",
                      "viaAggregator": True, "sourceKind": "aggregator", "verification": "unverified", "status": "active",
                      "matchType": "exactMatch"}])
    out, _, report = go(tmp_path, {"A": [], "2K": []}, az=az)
    j = {x["id"]: x for x in out["jobs"]}["az-5"]
    assert j["url"] == "https://adzuna/5" and j["ats"] == "adzuna"
    assert report["summary"]["aggregatorJobs"] == 1 and report["summary"]["officialJobs"] == 0

def test_partial_adzuna_run_does_not_close_adzuna_jobs(tmp_path):
    setup(tmp_path, COS)
    az1 = az_fetcher([{"id": "az-5", "company": "Zeta", "title": "VFX Artist", "url": "u", "ats": "adzuna", "viaAggregator": True,
                       "status": "active", "matchType": "exactMatch"}])
    go(tmp_path, {"A": [], "2K": []}, az=az1)
    out, _, _ = go(tmp_path, {"A": [], "2K": []}, az=az_fetcher([], status="partial"), now=NOW2)
    assert {x["id"]: x for x in out["jobs"]}["az-5"]["status"] == "active"

def test_disabled_company_is_skipped_not_failed(tmp_path):
    cos = [dict(COS[0], enabled=False), COS[1]]
    setup(tmp_path, cos)
    out, statuses, _ = go(tmp_path, {"A": [gh(1)], "2K": [gh(2)]})
    assert {s["company"]: s["status"] for s in statuses if "company" in s}["A"] == "disabled"
    assert out["companiesFailed"] == 0 and out["totalVfxJobs"] == 1

def test_legacy_jobs_json_is_migrated_on_load(tmp_path):
    setup(tmp_path, COS)
    legacy = {"lastUpdated": "2026-10-01T00:00:00Z", "jobs": [
        {"id": "gh-77", "company": "A", "title": "VFX Artist", "url": "https://x/77", "location": "Madrid", "workplaceType": "unknown",
         "remoteScope": "Unknown", "ats": "greenhouse", "matchType": "exactMatch", "firstSeen": NOW1, "lastSeen": NOW1, "status": "active"}]}
    (tmp_path / "jobs.json").write_text(json.dumps(legacy))
    out, _, _ = go(tmp_path, {"A": [gh(77)], "2K": []})
    j = out["jobs"][0]
    assert j["firstSeen"] == NOW1                      # conserva la primera detección
    assert j["spainEligibility"] in ("confirmed", "possible", "unknown", "restricted", "contradiction")


def test_error_kind_classification():
    from scanner.scanner import _error_kind
    assert _error_kind("HTTPSConnectionPool: Failed to resolve 'x' ([Errno -2] Name or service not known)") == "network"
    assert _error_kind("No response from https://2k.com/careers") == "timeout"
    assert _error_kind("HTTP 403 Forbidden") == "blocked"
    assert _error_kind("Invalid JSON from API") == "parse"
