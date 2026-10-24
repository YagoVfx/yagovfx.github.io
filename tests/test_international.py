from types import SimpleNamespace
import pytest
from scanner.adapters import international


def test_capcom_translates_explicit_vfx_role_preserves_original_and_skips_other_jobs(monkeypatch):
    listing='<a href="https://hrmos.co/pages/capcom/jobs/01_03_080"><h2>エフェクトデザイナー</h2></a><a href="https://hrmos.co/pages/capcom/jobs/02"><h2>Accountant</h2></a>'
    detail='<table><tr><th>勤務地</th><td>大阪</td></tr></table>'
    monkeypatch.setattr(international,'http_get',lambda u:SimpleNamespace(content=(listing if u.endswith('/jobs') else detail).encode()))
    adapter=international.CapcomAdapter({'name':'Capcom','careersUrl':'https://hrmos.co/pages/capcom/jobs'})
    job,=adapter.fetch_jobs()
    assert job['title']=='VFX Artist — エフェクトデザイナー'
    assert job['location']=='Osaka, Japan' and adapter.total_seen==2
    assert job['viaAggregator'] is False and adapter.listing_verified


def test_rovio_listing_change_does_not_silently_close_jobs(monkeypatch):
    monkeypatch.setattr(international,'http_get',lambda _:SimpleNamespace(content=b'<h1>Loading jobs</h1>'))
    adapter=international.RovioAdapter({'name':'Rovio','careersUrl':'https://www.rovio.com/open-positions/'})
    with pytest.raises(RuntimeError,match='unrecognized'):
        adapter.fetch_jobs()
