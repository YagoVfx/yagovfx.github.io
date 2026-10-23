import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scanner.classify import (classify_spain_eligibility as elig, classify_contract, classify_hours,
                              detect_seniority, detect_role, enrich_job, compatibility_of)


# DATA-03
def test_remote_us_only_is_restricted_with_reason():
    st, why = elig("Senior VFX Artist", "Remote - US only")
    assert st == "restricted" and "EE. UU." in why

def test_must_be_based_in_us_in_description_is_restricted():
    st, _ = elig("VFX Artist", "Remote", "You must be located in the United States to apply.")
    assert st == "restricted"

# DATA-04
def test_remote_europe_without_contract_is_possible_and_contract_unknown():
    j = enrich_job({"title": "Technical VFX Artist", "location": "Remote - Europe", "workplaceType": "remote",
                    "ats": "greenhouse", "url": "https://x/1"})
    assert j["spainEligibility"] == "possible"
    assert j["contractType"] == "unknown" and j["contractEvidence"] == ""

def test_confirmed_requires_explicit_spain_and_official_source():
    off = enrich_job({"title": "VFX Artist", "location": "Remote - Spain", "workplaceType": "remote", "ats": "lever", "url": "u"})
    agg = enrich_job({"title": "VFX Artist", "location": "Remote - Spain", "workplaceType": "remote", "ats": "adzuna",
                      "viaAggregator": True, "url": "u"})
    assert off["spainEligibility"] == "confirmed"
    assert agg["spainEligibility"] == "possible"       # un agregador nunca confirma

def test_generic_location_alone_never_confirms():
    j = enrich_job({"title": "VFX Artist", "location": "Madrid, Spain", "workplaceType": "unknown", "ats": "lever", "url": "u"})
    assert j["spainEligibility"] == "unknown"

def test_contradiction_goes_to_review_not_confirmed():
    st, _ = elig("VFX Artist", "Remote - Spain", "Candidates must be based in the UK. UK residents only.")
    assert st == "contradiction"
    assert compatibility_of("contradiction", "unknown", "unknown") == "review"

# DATA-05
def test_freelance_b2b_is_incompatible_even_if_remote_worldwide():
    j = enrich_job({"title": "Freelance VFX Artist (B2B)", "location": "Remote - Worldwide", "workplaceType": "remote",
                    "ats": "greenhouse", "url": "u"})
    assert j["contractType"] == "freelance" and j["compatibility"] == "incompatible"
    assert j["spainEligibility"] == "possible"          # geografía y contrato son independientes

def test_fulltime_does_not_imply_employee_contract():
    assert classify_contract("Full-time VFX Artist")[0] == "unknown"
    assert classify_hours("Full-time VFX Artist") == "full"
    assert classify_contract("Permanent, full-time")[0] == "employee"

def test_temporary_and_part_time():
    assert classify_contract("12-month contract")[0] == "temporary"
    assert enrich_job({"title": "VFX Artist part-time", "location": "Remote - Spain", "workplaceType": "remote",
                       "ats": "lever", "url": "u"})["compatibility"] == "incompatible"

def test_unknown_is_not_negative_evidence():
    j = enrich_job({"title": "Senior VFX Artist", "location": "", "workplaceType": "unknown", "ats": "greenhouse", "url": "u"})
    assert j["compatibility"] == "review"               # a revisar, no descartada
    assert j["relevance"]["score"] > 0
    assert any("no es rechazo" in r for r in j["relevance"]["reasons"])

def test_seniority_and_role_and_engine():
    assert detect_seniority("Lead VFX Artist") == "lead" and detect_seniority("Sr. FX Artist") == "senior"
    assert detect_role("Technical VFX Artist") == "tech-vfx" and detect_role("Technical Artist") == "technical-artist"
    j = enrich_job({"title": "VFX Artist", "location": "", "ats": "lever", "url": "u"}, "Niagara in Unreal Engine 5")
    assert "unreal" in j["engines"]

def test_ranking_prefers_confirmed_employee_over_restricted():
    best = enrich_job({"title": "Senior VFX Artist", "location": "Remote - Spain", "workplaceType": "remote", "ats": "greenhouse", "url": "u"},
                      "permanent contract")
    worst = enrich_job({"title": "Senior VFX Artist", "location": "Remote - US only", "workplaceType": "remote", "ats": "adzuna", "viaAggregator": True, "url": "u"})
    assert best["relevance"]["score"] > worst["relevance"]["score"]
    assert best["relevance"]["reasons"] and all(isinstance(r, str) for r in best["relevance"]["reasons"])

def test_enrich_is_idempotent_and_does_not_store_description():
    j = {"title": "VFX Artist", "location": "Remote", "ats": "lever", "url": "u"}
    a = enrich_job(dict(j), "secret long description permanent")
    assert "description" not in a
    assert enrich_job(dict(a))["relevance"]["score"] >= 0


def test_legacy_remote_scope_us_is_restricted_and_europe_possible():
    base = {"title": "VFX Artist", "location": "Remote", "workplaceType": "remote", "ats": "greenhouse", "url": "u"}
    assert enrich_job(dict(base, remoteScope="US"))["spainEligibility"] == "restricted"
    assert enrich_job(dict(base, remoteScope="Canada"))["spainEligibility"] == "restricted"
    assert enrich_job(dict(base, remoteScope="EU/Europe"))["spainEligibility"] == "possible"
    assert enrich_job(dict(base, remoteScope="Spain"))["spainEligibility"] == "confirmed"
    assert enrich_job(dict(base, remoteScope="unknown"))["spainEligibility"] == "unknown"

def test_non_artist_vfx_roles_do_not_score_as_vfx_artist():
    assert detect_role("VFX Producer - Senior") == "other"
    assert detect_role("VFX Coordinator") == "other"
    assert detect_role("Senior VFX Artist") == "vfx"
    assert detect_role("VFX Supervisor") == "vfx"


def test_not_remote_and_elsewhere_penalise_ranking_but_never_reject():
    base = {"title": "Senior VFX Artist", "ats": "greenhouse", "url": "u"}
    remote = enrich_job(dict(base, location="Remote - Europe", workplaceType="remote"))
    onsite = enrich_job(dict(base, location="Warsaw, Poland", workplaceType="onsite"))
    elsewhere = enrich_job(dict(base, location="Montreal, Canada", workplaceType="unknown"))
    assert remote["relevance"]["score"] > elsewhere["relevance"]["score"] > onsite["relevance"]["score"]
    assert onsite["compatibility"] == "review" and elsewhere["compatibility"] == "review"   # no se oculta ni se rechaza
    assert any("no es 100" in r for r in onsite["relevance"]["reasons"])
