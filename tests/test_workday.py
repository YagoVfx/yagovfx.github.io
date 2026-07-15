import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.adapters.workday import parse_workday_url


def test_parse_basic_tenant_site():
    tenant, host, site = parse_workday_url(
        "https://activision.wd1.myworkdayjobs.com/Blizzard_External_Careers"
    )
    assert tenant == "activision"
    assert host == "wd1"
    assert site == "Blizzard_External_Careers"


def test_parse_with_locale_prefix():
    tenant, host, site = parse_workday_url(
        "https://ea.wd1.myworkdayjobs.com/en-US/Electronic_Arts"
    )
    assert tenant == "ea"
    assert site == "Electronic_Arts"


def test_parse_returns_none_for_non_workday_url():
    assert parse_workday_url("https://boards.greenhouse.io/example") is None
    assert parse_workday_url("") is None


if __name__ == "__main__":
    test_parse_basic_tenant_site()
    test_parse_with_locale_prefix()
    test_parse_returns_none_for_non_workday_url()
    print("All tests passed.")
