"""Regression checks for the real employer integrations added on 2026-10-23."""
from unittest.mock import Mock, patch
import pytest
from scanner.adapters.ea import EaAdapter
from scanner.adapters.epic import EpicAdapter
from scanner.adapters.company_feeds import BambooAdapter, PinpointAdapter, Room8Adapter


def html(text):
    return Mock(content=text.encode(), text=text)


def payload(data, headers=None):
    response = Mock(headers=headers or {})
    response.json.return_value = data
    return response


def card(ident, studio="EA Studios - Respawn"):
    return f'''<article class="article article--result"><a class="link_result" href="https://jobs.ea.com/en_US/careers/JobDetail/VFX-Artist/{ident}">VFX Artist</a>
      <span class="list-item-department">{studio}</span><span class="list-item-location">Vancouver, Canada</span></article>'''


DETAIL = '''<main><h1>VFX Artist</h1><div class="article__content__view__field">
<div class="article__content__view__field__label">Studio/Department</div><div class="article__content__view__field__value">EA Studios - Respawn</div></div>
<div class="article__content__view__field"><div class="article__content__view__field__label">Work Model</div><div class="article__content__view__field__value">Hybrid</div></div>
Regular Employee. Full-time. Must reside in the United States.</main>'''


def test_respawn_follows_pages_and_never_attributes_other_ea_studios():
    adapter = EaAdapter({"name": "Respawn", "careersUrl": "https://jobs.ea.com/en_US/careers/SearchJobs/", "studioFilter": "Respawn"})
    page1 = card(1, "EA Studios - SPORTS") + '<a href="https://jobs.ea.com/en_US/careers/SearchJobs/VFX?jobOffset=20">Next &gt;&gt;</a>'
    def get(url):
        if "/JobDetail/" in url:
            return html(DETAIL)
        if "jobOffset=20" in url:
            return html(card(2))
        if "search=effects" in url:
            return html('<div class="results">No jobs found</div>')
        return html(page1)
    with patch("scanner.adapters.ea.http_get", side_effect=get):
        jobs = adapter.fetch_jobs()
    assert [j["id"] for j in jobs] == ["ea-2"]
    assert jobs[0]["company"] == "Respawn" and jobs[0]["workplaceType"] == "hybrid"
    assert jobs[0]["spainEligibility"] == "restricted"
    assert adapter.listing_verified and not adapter.incomplete


def test_ea_changed_layout_is_not_reported_as_empty_success():
    with patch("scanner.adapters.ea.http_get", return_value=html('<h1>Sorry, maintenance</h1>')):
        with pytest.raises(RuntimeError, match="layout"):
            EaAdapter({"name": "EA", "careersUrl": "https://jobs.ea.com"}).fetch_jobs()


def test_ea_partial_listing_never_closes_old_jobs_as_a_complete_scan():
    adapter = EaAdapter({"name": "EA", "careersUrl": "https://jobs.ea.com"})
    def get(url):
        if "search=effects" in url:
            return html('<div class="results">No jobs found</div>')
        if "jobOffset=20" in url:
            return None
        return html('<div class="results"></div><a href="/en_US/careers/SearchJobs/?jobOffset=20">Next</a>')
    with patch("scanner.adapters.ea.http_get", side_effect=get):
        assert adapter.fetch_jobs() == []
    assert adapter.incomplete


def test_epic_fetches_final_page_and_job_description():
    adapter = EpicAdapter({"name": "Epic Games", "careersUrl": "https://www.epicgames.com/site/en-US/careers/jobs"})
    first = [{"id": n, "title": "Accountant"} for n in range(100)]
    last = {"id": 100, "title": "Senior VFX Artist", "absolute_url": "https://epicgames.com/careers/jobs/100", "location": {"name": "Remote, Spain"}}
    responses = [payload({"hits": first, "total": 101}), payload({"hits": [last], "total": 101}), payload({"content": "<p>Full-time permanent employee</p>", "first_published": "2026-10-23"})]
    with patch("scanner.adapters.epic.http_get", side_effect=responses) as get:
        jobs = adapter.fetch_jobs()
    assert "skip=100" in get.call_args_list[1].args[0]
    assert len(jobs) == 1 and jobs[0]["id"] == "gh-100"
    assert jobs[0]["sourceKind"] == "ats" and jobs[0]["postedDate"] == "2026-10-23"
    assert adapter.total_seen == 101 and not adapter.incomplete


def test_epic_repeated_page_is_incomplete_not_empty_complete():
    adapter = EpicAdapter({"name": "Epic", "careersUrl": "https://www.epicgames.com/site/en-US/careers/jobs"})
    response = payload({"hits": [{"id": 1, "title": "Accountant"}], "total": 2})
    with patch("scanner.adapters.epic.http_get", return_value=response):
        assert adapter.fetch_jobs() == []
    assert adapter.incomplete


def test_bamboo_empty_official_feed_is_valid_but_error_response_is_not():
    company = {"name": "Ember Lab", "careersUrl": "https://emberlab.bamboohr.com/careers"}
    with patch("scanner.adapters.company_feeds.http_get", return_value=payload({"success": True, "departments": []})):
        assert BambooAdapter(company).fetch_jobs() == []
    with patch("scanner.adapters.company_feeds.http_get", return_value=payload({"success": False})):
        with pytest.raises(RuntimeError, match="schema"):
            BambooAdapter(company).fetch_jobs()


def test_pinpoint_empty_vs_unrecognized_nonempty_schema():
    company = {"name": "Build A Rocket Boy", "careersUrl": "https://buildarocketboy.pinpointhq.com/en"}
    with patch("scanner.adapters.company_feeds.http_get", return_value=payload({"data": []})):
        adapter = PinpointAdapter(company)
        assert adapter.fetch_jobs() == [] and not adapter.incomplete
    with patch("scanner.adapters.company_feeds.http_get", return_value=payload({"data": [{"unexpected": True}]})):
        adapter = PinpointAdapter(company)
        assert adapter.fetch_jobs() == [] and adapter.incomplete


def test_room8_reads_both_feeds_paginates_and_keeps_location_evidence():
    adapter = Room8Adapter({"name": "Room8", "careersUrl": "https://room8group.com/join-the-team/"})
    row = {"id": 5, "title": {"rendered": "Realtime VFX Artist"}, "content": {"rendered": "<p>Permanent employee</p>"},
           "link": "https://room8group.com/join-the-team/vfx/", "date_gmt": "2026-10-23T12:00:00",
           "_embedded": {"wp:term": [[{"name": "Spain", "taxonomy": "tlocation"}, {"name": "Remote", "taxonomy": "tcoop"}]]}}
    with patch("scanner.adapters.company_feeds.http_get", side_effect=[payload([], {"X-WP-TotalPages": "2"}), payload([row], {"X-WP-TotalPages": "2"}), payload([], {"X-WP-TotalPages": "1"})]) as get:
        jobs = adapter.fetch_jobs()
    assert "page=2" in get.call_args_list[1].args[0]
    assert "room8studio.com" in get.call_args_list[2].args[0]
    assert jobs[0]["location"] == "Spain" and jobs[0]["workplaceType"] == "remote"
    assert not adapter.incomplete
