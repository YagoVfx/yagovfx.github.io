import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.filters import classify_job, detect_workplace, detect_remote_scope

def test_exact_matches():
    assert classify_job("Senior VFX Artist") == "exactMatch"
    assert classify_job("Lead FX Artist") == "exactMatch"
    assert classify_job("Real-Time VFX Artist") == "exactMatch"
    assert classify_job("Junior VFX Artist") == "exactMatch"
    assert classify_job("VFX Supervisor") == "exactMatch"
    assert classify_job("Realtime VFX") == "exactMatch"

def test_exclusions():
    assert classify_job("Compositor") is None
    assert classify_job("Compositing Artist") is None
    assert classify_job("Motion Graphics Designer") is None

def test_possible_match():
    # POSSIBLE_TITLE requires the VFX-ish term to be in the TITLE (bare "fx",
    # "vfx", "particle"...) — the description alone only confirms it, it
    # can't carry the match on its own. "Technical Artist" (no fx/vfx word
    # at all) can never satisfy this, regardless of description.
    desc = "Uses Niagara for particle FX and real-time FX systems"
    assert classify_job("FX Technical Artist", desc) == "possibleMatch"

def test_bare_vfx_word_fallback():
    assert classify_job("VFX Generalist") == "possibleMatch"
    assert classify_job("VFX (all levels)") == "possibleMatch"
    assert classify_job("Software Engineer") is None

def test_workplace():
    assert detect_workplace("", "Remote - EU", "") == "remote"
    assert detect_workplace("", "Hybrid, Warsaw", "") == "hybrid"
    assert detect_workplace("", "On-site, Madrid", "") == "onsite"

def test_remote_scope():
    assert detect_remote_scope("", "Remote - Europe") == "EU/Europe"
    assert detect_remote_scope("", "Remote US Only") == "US"
    assert detect_remote_scope("", "Remote - Spain") == "Spain"
    assert detect_remote_scope("", "Warsaw, Poland") == "Unknown"

if __name__ == "__main__":
    test_exact_matches()
    test_exclusions()
    test_possible_match()
    test_bare_vfx_word_fallback()
    test_workplace()
    test_remote_scope()
    print("All tests passed.")
