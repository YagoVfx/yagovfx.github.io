"""Validación OFFLINE de la configuración de empresas y del registro (sin red)."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pytest
from scanner.scanner import ATS_MAP, resolve_ats
from scanner import build_registry
from scanner.adapters.greenhouse import extract_greenhouse_board
from scanner.adapters.lever import extract_lever_company
from scanner.adapters.smartrecruiters import extract_smartrecruiters_company
from scanner.adapters.personio import extract_personio_subdomain
from scanner.adapters.ashby import extract_ashby_board

DATA = Path(__file__).parent.parent / "data"
COMPANIES = json.loads((DATA / "companies.json").read_text(encoding="utf-8"))
REG = json.loads((DATA / "companies-registry.json").read_text(encoding="utf-8"))
EXTRACT = {"greenhouse": extract_greenhouse_board, "lever": extract_lever_company,
           "smartrecruiters": extract_smartrecruiters_company, "personio": extract_personio_subdomain, "ashby": extract_ashby_board}


@pytest.mark.parametrize("c", COMPANIES, ids=[c["name"] for c in COMPANIES])
def test_every_configured_company_resolves_to_an_adapter_that_can_read_its_url(c):
    ats = resolve_ats(c)
    assert ats in ATS_MAP, f"{c['name']}: ATS «{ats}» sin adaptador"
    assert re.match(r"^https?://", c["careersUrl"])
    if ats in EXTRACT:
        assert EXTRACT[ats](c["careersUrl"]), f"{c['name']}: no se puede extraer el identificador de {c['careersUrl']}"


def test_company_names_and_urls_are_unique():
    assert len({c["name"].lower() for c in COMPANIES}) == len(COMPANIES)
    assert len({c["careersUrl"].rstrip("/").lower() for c in COMPANIES}) == len(COMPANIES)


def test_required_studios_are_configured():
    names = {c["name"] for c in COMPANIES}
    assert {"Mundfish", "AXIOM VFX"} <= names


def test_registry_schema_and_enums():
    allowed_state = {"active", "unsupported", "blocked", "pending"}
    for e in REG["companies"]:
        assert e["state"] in allowed_state, e["name"]
        assert e["reliability"] in {"alta", "media", "baja", "desconocida"}
        assert e["priority"] in {"alta", "media", "baja"}
        assert e["evidence"]["kind"] in {"scanner-run", "web-research", "discovery-cache", "none"}
        assert e["reason"], f"{e['name']}: falta el motivo"
        for k in ("officialUrl", "careersUrl"):
            assert e.get(k) is None or re.match(r"^https?://", e[k]), (e["name"], k)
        if e["state"] == "active":
            assert e["evidence"]["kind"] == "scanner-run", "«active» exige evidencia de un escaneo real"
    assert len({e["name"].lower() for e in REG["companies"]}) == len(REG["companies"]), "nombres duplicados en el registro"


def test_registry_never_claims_connected_without_real_run_and_counts_are_honest():
    t = REG["totals"]
    assert t["registered"] == len(REG["companies"])
    assert t["withDirectEvidence"] == sum(1 for e in REG["companies"] if e["evidence"]["kind"] in ("scanner-run", "web-research"))
    assert t["withDirectEvidence"] < t["registered"]          # las candidatas sin evidencia NO cuentan como evaluadas
    assert sum(t["byState"].values()) == t["registered"]
    for e in REG["companies"]:
        if e.get("configuredNotYetRun"):
            assert e["state"] == "pending"


def test_registry_has_no_emails_tokens_or_secrets():
    blob = json.dumps(REG) + json.dumps(COMPANIES)
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", blob), "no deben publicarse emails"
    assert not re.search(r"ghp_|github_pat_|api[_-]?key|secret|token", blob, re.I)


def test_researched_studios_are_in_registry_with_their_evidence():
    by = {e["name"]: e for e in REG["companies"]}
    for n in ("Mundfish", "AXIOM VFX", "Larian Studios", "IO Interactive", "Digital Sun Games", "Escape Velocity Entertainment", "MercurySteam"):
        assert n in by and by[n]["evidence"]["kind"] == "web-research", n
    assert "contratación laboral NO acreditada" in by["AXIOM VFX"]["reason"]
    assert by["Mundfish"]["state"] == "pending"                   # adaptador listo pero sin ejecución real


def test_registry_is_reproducible_from_sources():
    fresh = build_registry.build(DATA)
    assert fresh["totals"] == REG["totals"]
    assert [e["name"] for e in fresh["companies"]] == [e["name"] for e in REG["companies"]]
