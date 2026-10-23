import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scanner.lifecycle import reconcile, merge_aggregator_into_official, prune_closed

T0, T1 = "2026-10-01T00:00:00Z", "2026-10-08T00:00:00Z"

def job(i, company="Co", ats="greenhouse", status="active", **kw):
    d = {"id": i, "company": company, "title": "VFX", "ats": ats, "status": status, "lastSeen": T0, "firstSeen": T0}
    d.update(kw); return d

OK_REL = {"ok": True, "reliable": True, "complete": True}

# DATA-01
def test_failed_source_does_not_close_jobs():
    ex = {"a": job("a", "2K")}
    out = reconcile(ex, {}, {"company:2K": {"ok": False, "error": "No response from 2k.com/careers"}}, T1)
    assert out["a"]["status"] == "active" and out["a"]["lastSeen"] == T0
    assert "No response" in out["a"]["lastError"]

def test_source_missing_from_outcomes_is_treated_as_failed():
    out = reconcile({"a": job("a")}, {}, {}, T1)
    assert out["a"]["status"] == "active"

def test_long_failure_makes_stale_never_closed():
    ex = {"a": job("a", lastSeen="2026-09-01T00:00:00Z")}
    out = reconcile(ex, {}, {"company:Co": {"ok": False}}, T1)
    assert out["a"]["status"] == "stale"

def test_truncated_result_does_not_close():
    out = reconcile({"a": job("a")}, {}, {"company:Co": {"ok": True, "reliable": True, "complete": False}}, T1)
    assert out["a"]["status"] == "active"

def test_successful_reliable_scan_closes_and_keeps_lastseen():
    out = reconcile({"a": job("a")}, {}, {"company:Co": OK_REL}, T1)
    assert out["a"]["status"] == "closed" and out["a"]["closedAt"] == T1 and out["a"]["lastSeen"] == T0

def test_unreliable_source_needs_consecutive_misses():
    o = {"company:Co": {"ok": True, "reliable": False, "complete": True}}
    cur = {"a": job("a")}
    states = []
    for n in range(3):
        cur = reconcile(cur, {}, o, T1); states.append(cur["a"]["status"])
    assert states == ["stale", "stale", "closed"]

def test_closed_jobs_are_not_touched_again_and_get_pruned():
    ex = {"a": job("a", status="closed", closedAt="2026-08-01T00:00:00Z", lastSeen=T0),
          "b": job("b", status="closed", closedAt="2026-10-05T00:00:00Z", lastSeen=T0)}
    out = reconcile(ex, {}, {"company:Co": OK_REL}, T1)
    assert "a" not in out                              # >30 días cerrada: podada
    assert out["b"]["lastSeen"] == T0                  # nunca se sobrescribe

def test_reopen_when_it_reappears():
    ex = {"a": job("a", status="closed", closedAt=T0)}
    out = reconcile(ex, {"a": job("a")}, {"company:Co": OK_REL}, T1)
    assert out["a"]["status"] == "active" and "closedAt" not in out["a"] and out["a"]["lastSeen"] == T1

def test_adzuna_never_closes_official_job():
    ex = {"gh": job("gh", "Studio"), "az": job("az", "Studio", ats="adzuna", viaAggregator=True)}
    out = reconcile(ex, {}, {"adzuna": {"ok": True, "reliable": False, "complete": True},
                             "company:Studio": {"ok": False, "error": "timeout"}}, T1)
    assert out["gh"]["status"] == "active"             # su fuente falló: intacta
    assert out["az"]["status"] == "stale"              # la de Adzuna sí avanza (1ª ausencia)

# DATA-02
def match(a, b): return a.lower() == b.lower()

def test_same_vacancy_in_ats_and_adzuna_is_merged_official_wins():
    official = {"gh-1": job("gh-1", "Embark Studios", sourceKind="ats", title="Senior VFX Artist")}
    az = [{"id": "az-1", "company": "embark studios", "title": "SENIOR VFX ARTIST", "ats": "adzuna"},
          {"id": "az-2", "company": "Other", "title": "Senior VFX Artist", "ats": "adzuna"}]
    kept, merged = merge_aggregator_into_official(az, official, match)
    assert [k["id"] for k in kept] == ["az-2"] and merged == 1
    assert official["gh-1"]["alsoSeenIn"] == ["adzuna"]

def test_aggregator_entries_never_suppress_other_aggregator_entries():
    prev = {"az-old": job("az-old", "Embark Studios", ats="adzuna", viaAggregator=True, sourceKind="aggregator")}
    kept, merged = merge_aggregator_into_official([{"id": "az-new", "company": "Embark Studios", "title": "VFX"}], prev, match)
    assert len(kept) == 1 and merged == 0
