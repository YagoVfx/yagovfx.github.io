import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.company_category import classify_company_category, is_known_aaa_studio


def test_known_aaa_studios_detected():
    assert classify_company_category("Rockstar Games") == "aaa"
    assert classify_company_category("Rockstar North") == "aaa"
    assert classify_company_category("Electronic Arts") == "aaa"
    assert classify_company_category("EA Vancouver") == "aaa"
    assert classify_company_category("Ubisoft Montreal") == "aaa"
    assert classify_company_category("2K Games") == "aaa"
    assert classify_company_category("CD Projekt Red") == "aaa"
    # Regression: the user's own companies.json entry is named "CD Project"
    # (no "k") — the alias list must cover this common spelling too, not
    # just the studio's official "Projekt" spelling.
    assert classify_company_category("CD Project") == "aaa"


def test_unknown_studios_default_to_indie():
    assert classify_company_category("Lighthouse Games") == "indie"
    assert classify_company_category("Some Random Indie Co") == "indie"
    assert classify_company_category("") == "indie"


def test_no_false_positive_on_short_alias():
    # "EA" as a standalone word shouldn't match inside an unrelated word.
    assert classify_company_category("Eagle Games") == "indie"
    assert is_known_aaa_studio("Eagle Games") is False


def test_manual_override_always_wins():
    assert classify_company_category("Rockstar Games", manual_override="indie") == "indie"
    assert classify_company_category("Some Tiny Studio", manual_override="aaa") == "aaa"
    # Invalid/garbage override falls back to automatic classification.
    assert classify_company_category("Rockstar Games", manual_override="bogus") == "aaa"


if __name__ == "__main__":
    test_known_aaa_studios_detected()
    test_unknown_studios_default_to_indie()
    test_no_false_positive_on_short_alias()
    test_manual_override_always_wins()
    print("All tests passed.")
