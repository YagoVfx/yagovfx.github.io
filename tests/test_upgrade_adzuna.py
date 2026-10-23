"""V2: el antiguo «upgrade» de Adzuna a enlace directo se sustituye por
attach_company_careers_links. La expectativa antigua (cambiar url/ats/
viaAggregator a los del tablero de la empresa) era el defecto auditado: una
vacante de Adzuna se hacía pasar por oficial con la URL de una landing."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.scanner import attach_company_careers_links, migrate_legacy_job

BOARD = "https://job-boards.greenhouse.io/gramgamescareers"
CACHE = {"gram games": {"found": True, "ats": "greenhouse", "careersUrl": BOARD, "checkedAt": 0}}


def test_adds_board_link_without_touching_the_vacancy_url_or_source():
    jobs = [{"id": "az-1", "company": "Gram Games", "title": "VFX Artist",
             "url": "https://adzuna.es/land/ad/1", "ats": "adzuna", "viaAggregator": True}]
    out, count = attach_company_careers_links(jobs, CACHE)
    assert count == 1
    j = out[0]
    assert j["url"] == "https://adzuna.es/land/ad/1"      # NO se sustituye por la landing
    assert j["ats"] == "adzuna"                              # sigue siendo Adzuna
    assert j["viaAggregator"] is True                        # sigue siendo agregador
    assert j["companyCareersUrl"] == BOARD and j["companyAts"] == "greenhouse"
    assert "companyCareersUrl" not in jobs[0]                # sin mutar el original


def test_leaves_job_unchanged_when_no_discovery_match():
    cache = {"totally unknown studio": {"found": False, "checkedAt": 9999999999}}
    jobs = [{"id": "az-2", "company": "Totally Unknown Studio", "title": "VFX Artist",
             "url": "https://adzuna.es/land/ad/2", "ats": "adzuna", "viaAggregator": True}]
    out, count = attach_company_careers_links(jobs, cache)
    assert count == 0 and out[0] == jobs[0]


def test_only_probes_each_company_once_per_run():
    jobs = [{"id": "az-1", "company": "Gram Games", "title": "A", "url": "x", "ats": "adzuna", "viaAggregator": True},
            {"id": "az-2", "company": "Gram Games", "title": "B", "url": "y", "ats": "adzuna", "viaAggregator": True}]
    out, count = attach_company_careers_links(jobs, CACHE)
    assert count == 2 and all(j["viaAggregator"] is True for j in out)


def test_legacy_upgraded_record_is_reverted_to_aggregator_signal():
    legacy = {"id": "az-5896092475", "company": "Scopely", "title": "Senior VFX Artist", "ats": "greenhouse",
              "url": "https://job-boards.greenhouse.io/scopely", "viaAggregator": False, "location": "Barcelona, Spain",
              "workplaceType": "unknown", "remoteScope": "Unknown", "matchType": "exactMatch", "status": "active"}
    j = migrate_legacy_job(dict(legacy))
    assert j["ats"] == "adzuna" and j["viaAggregator"] is True
    assert j["sourceKind"] == "aggregator" and j["verification"] == "unverified"
    assert j["companyCareersUrl"] == legacy["url"] and j["companyAts"] == "greenhouse"
    assert j["urlIsLanding"] is True and j["directUrl"] is False
    assert migrate_legacy_job(dict(j)) == j                  # idempotente
