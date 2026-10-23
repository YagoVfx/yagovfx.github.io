import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pytest
import scanner.adapters.official_sites as os_mod
from scanner.adapters.official_sites import MundfishAdapter, AxiomVfxAdapter
from scanner.companies import detect_ats
from scanner.scanner import resolve_ats
from scanner.classify import classify_contract, classify_hours

FIX = Path(__file__).parent / "fixtures"

class _Resp:
    def __init__(self, text): self.text = text

def serve(monkeypatch, name):
    monkeypatch.setattr(os_mod, "http_get", lambda url, *a, **k: _Resp((FIX / name).read_text(encoding="utf-8")))

MF = {"name": "Mundfish", "careersUrl": "https://mundfish.com/en/careers"}
AX = {"name": "AXIOM VFX", "careersUrl": "https://www.axiomvfx.com/career"}


def test_hosts_are_routed_to_their_own_adapters_even_when_declared_custom():
    assert detect_ats("https://mundfish.com/en/careers") == "mundfish"
    assert detect_ats("https://www.axiomvfx.com/career") == "axiomvfx"
    assert resolve_ats({"type": "custom", **MF}) == "mundfish"
    assert resolve_ats({"type": "custom", **AX}) == "axiomvfx"

def test_mundfish_keeps_only_vfx_roles_from_the_official_list(monkeypatch):
    serve(monkeypatch, "mundfish_careers.html")
    a = MundfishAdapter(MF)
    jobs = a.fetch_jobs()
    titles = {j["title"] for j in jobs}
    # El filtro de títulos del proyecto solo admite roles VFX: «Technical Artist» a secas queda fuera
    assert titles == {"VFX Artist"}
    assert a.total_seen == 5                      # 5 vacantes distintas pese a los 3 enlaces por tarjeta
    assert a.uses_reliable_api is False

def test_mundfish_vfx_artist_is_specific_url_official_remote_global_contract_unknown(monkeypatch):
    serve(monkeypatch, "mundfish_careers.html")
    j = {x["title"]: x for x in MundfishAdapter(MF).fetch_jobs()}["VFX Artist"]
    assert j["url"] == "https://mundfish.com/careers/vfx-artist"             # ficha concreta, no la landing
    assert j["id"] == "mf-vfx-artist" and j["ats"] == "custom"
    assert j["sourceKind"] == "official-site" and j["verification"] == "verified" and j["directUrl"] is True
    assert j["workplaceType"] == "remote" and j["seniority"] == "senior"
    assert j["spainEligibility"] == "possible"                               # «global remote work», sin nombrar España
    assert j["contractType"] == "unknown" and j["contractEvidence"] == ""
    assert j["compatibility"] == "compatible" and j["relevance"]["score"] > 0
    assert "description" not in j

def test_mundfish_no_job_links_returns_empty_for_review_not_error(monkeypatch):
    monkeypatch.setattr(os_mod, "http_get", lambda *a, **k: _Resp("<html><body><h1>Careers</h1></body></html>"))
    assert MundfishAdapter(MF).fetch_jobs() == []

def test_no_response_raises_instead_of_pretending_zero(monkeypatch):
    monkeypatch.setattr(os_mod, "http_get", lambda *a, **k: None)
    for cls, c in ((MundfishAdapter, MF), (AxiomVfxAdapter, AX)):
        with pytest.raises(RuntimeError):
            cls(c).fetch_jobs()

def test_axiom_single_posting_with_ambiguous_contract_is_not_treated_as_employee(monkeypatch):
    serve(monkeypatch, "axiom_career.html")
    jobs = AxiomVfxAdapter(AX).fetch_jobs()
    assert len(jobs) == 1
    j = jobs[0]
    assert j["title"] == "Real-Time VFX Artist" and j["url"] == "https://www.axiomvfx.com/career"
    assert j["workplaceType"] == "remote" and j["spainEligibility"] == "possible"
    assert j["contractType"] == "unknown" and "full-time or contract" in j["contractEvidence"].lower()
    assert j["hours"] == "unknown"                                           # «full-time or contract» no acredita jornada completa
    assert any("ambigua" in r for r in j["relevance"]["reasons"])
    assert j["compatibility"] == "compatible"                                # no se oculta, pero la UI avisa de la ambigüedad

def test_axiom_without_recognisable_posting_returns_empty(monkeypatch):
    monkeypatch.setattr(os_mod, "http_get", lambda *a, **k: _Resp("<html><body><h1>About us</h1><p>We make VFX.</p></body></html>"))
    assert AxiomVfxAdapter(AX).fetch_jobs() == []

def test_ambiguous_contract_phrases():
    assert classify_contract("Remote, flexible engagement — full-time or contract") [0] == "unknown"
    assert classify_contract("Remote, flexible engagement — full-time or contract")[1].lower() == "full-time or contract"
    assert classify_hours("full-time or contract") == "unknown"
    assert classify_contract("B2B, full-time or contract")[0] == "freelance"        # lo explícito gana a lo ambiguo
