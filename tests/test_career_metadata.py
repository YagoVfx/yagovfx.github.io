from scanner.career_metadata import enrich_sources
from scanner.training_sources import sidefx


def test_sources_separate_professions_ats_and_training():
    rows = enrich_sources([dict(name=name) for name in ['Inditex · Recruitee', 'Veolia · SmartRecruiters', 'SideFX · videojuegos y VFX', 'SNE: electricista · Vigo']])
    assert rows[0]['platform'] == 'Recruitee'
    assert rows[0]['categories'] == ['programming']
    assert rows[1]['categories'] == ['electricity']
    assert rows[2]['categories'] == ['courses']
    assert rows[3]['categories'] == ['electricity']


def test_sidefx_changed_page_is_not_accepted_as_course(monkeypatch):
    import scanner.training_sources as module
    import pytest
    class Response:
        content = b'<h1>Page not found</h1>'
    monkeypatch.setattr(module, 'get', lambda url: Response())
    with pytest.raises(ValueError, match='title changed'):
        sidefx('2026-10-25T00:00:00Z')
