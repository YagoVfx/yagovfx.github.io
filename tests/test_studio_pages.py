from types import SimpleNamespace
import pytest
from scanner.adapters import studio_pages
from scanner.adapters.teamtailor import TeamtailorAdapter


def response(monkeypatch, html):
    monkeypatch.setattr(studio_pages, "http_get", lambda _: SimpleNamespace(text=html, content=html.encode()))


def test_inline_listing_counts_unrelated_roles_without_importing_them(monkeypatch):
    response(monkeypatch, '<h1>Infinite Plus</h1><button class="accordion"><div class="elementor-col-30">Level Designer</div></button><div class="panel">Unity role</div>')
    adapter = studio_pages.InfinitePlusAdapter(dict(name="Infinite Plus", careersUrl="https://infinite-plus.io/careers"))
    assert adapter.fetch_jobs() == []
    assert adapter.total_seen == 1 and adapter.listing_verified


def test_inline_vfx_description_does_not_invent_detail_url(monkeypatch):
    response(monkeypatch, '<h1>Infinite Plus</h1><button class="accordion"><div class="elementor-col-30">VFX Artist</div></button><div class="panel">Unity particle effects</div>')
    adapter = studio_pages.InfinitePlusAdapter(dict(name="Infinite Plus", careersUrl="https://infinite-plus.io/careers"))
    job, = adapter.fetch_jobs()
    assert job["urlIsLanding"] and job["directUrl"] is False
    assert job["viaAggregator"] is False


def test_changed_inline_schema_cannot_close_existing_jobs(monkeypatch):
    response(monkeypatch, '<h1>Infinite Plus</h1><div>Loading jobs...</div>')
    adapter = studio_pages.InfinitePlusAdapter(dict(name="Infinite Plus", careersUrl="https://infinite-plus.io/careers"))
    with pytest.raises(RuntimeError, match="schema changed"):
        adapter.fetch_jobs()


def test_mercury_requires_explicit_no_vacancies_statement(monkeypatch):
    adapter = studio_pages.MercurySteamAdapter(dict(name="MercurySteam", careersUrl="https://www.mercurysteam.com/talento/"))
    response(monkeypatch, 'MercurySteam: Hoy no tenemos posiciones abiertas.')
    assert adapter.fetch_jobs() == [] and adapter.listing_verified
    response(monkeypatch, 'MercurySteam: VFX Artist, apply now')
    with pytest.raises(RuntimeError, match="review new listing"):
        adapter.fetch_jobs()


def test_teamtailor_explicit_empty_board_is_distinct_from_loading_shell(monkeypatch):
    adapter = TeamtailorAdapter(dict(name="Funcom", careersUrl="https://jobs.funcom.com/jobs"))
    monkeypatch.setattr(adapter, "_get_jobs_page", lambda: '<p>No open positions right now</p><a href="https://www.teamtailor.com/">Teamtailor</a>')
    assert adapter.fetch_jobs() == [] and adapter.listing_verified
    monkeypatch.setattr(adapter, "_get_jobs_page", lambda: '<p>Loading...</p>')
    assert adapter.fetch_jobs() == [] and not adapter.listing_verified
