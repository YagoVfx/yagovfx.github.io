import pytest

from scanner.mobile_careers import classify_offer, course_available
from scanner.mobile_sources import permitted_remote


@pytest.mark.parametrize('location', ['Vigo', 'Teis, Vigo', 'Bouzas (Vigo)', 'Zona Franca, Vigo', 'Pol. Ind. Balaídos, Vigo'])
def test_vigo_neighborhoods_belong_to_municipality(location):
    assert classify_offer('Electricista', '', location)['inVigo']


def test_coruna_alias_and_other_municipalities():
    assert classify_offer('Electricista', '', 'Coruña, A')['inCoruna']
    for location in ['Arteixo, A Coruña', 'Nigrán, Vigo', 'Culleredo, A Coruña']:
        row = classify_offer('Electricista', '', location)
        assert not row['inVigo'] and not row['inCoruna']


def test_personal_responsibility_is_not_seniority():
    assert classify_offer('Electricista', 'Persona responsable. Experiencia de 1 año', 'Vigo')['experience'] == 'unknown'
    assert classify_offer('Senior developer', 'Minimum 5 years experience', 'Vigo')['experience'] == 'experienced'


@pytest.mark.parametrize('description', ['Remote - US', 'Remote U.S.', 'Remote from the US', 'Remote from Hong Kong', 'Remote work one day per week'])
def test_remote_board_cannot_override_country_or_hybrid_restrictions(description):
    assert not permitted_remote('Anywhere in the World', description)


def test_genuine_worldwide_remote_remains_available():
    assert permitted_remote('Anywhere in the World', 'Fully remote worldwide')


def test_closed_course_intakes_expire_but_continuous_enrolment_remains():
    assert not course_available({'startDate': '2026-10-20'}, '2026-10-26')
    assert course_available({'startDate': '2026-10-20', 'enrollmentStatus': 'continuous'}, '2026-10-26')
    assert course_available({'startDate': '2026-10-20', 'enrollmentEnd': '2026-10-28'}, '2026-10-26')
    assert not course_available({'enrollmentEnd': '2026-10-25'}, '2026-10-26')


def test_total_outage_preserves_last_success_date_and_expires_closed_intakes(tmp_path, monkeypatch):
    import json
    from scanner import mobile_careers as careers, mobile_sources, training_sources
    data = tmp_path / 'data'
    data.mkdir()
    previous = dict(updatedAt='2026-10-20T12:00:00Z', offers=[], courses=[
        dict(id='course-fundae-1', startDate='2000-01-01'),
        dict(id='course-fundae-2', title='Continuous learning')], sources=[])
    (data / 'mobile-careers.json').write_text(json.dumps(previous), encoding='utf-8')
    (data / 'jobs.json').write_text('{"jobs":[]}', encoding='utf-8')
    def fail(*args, **kwargs):
        raise RuntimeError('Simulated outage')
    monkeypatch.setattr(careers, 'ROOT', tmp_path)
    monkeypatch.setattr(careers.SneSearch, 'search', fail)
    monkeypatch.setattr(careers, 'workable_programming', fail)
    monkeypatch.setattr(careers, 'fundae_courses', fail)
    monkeypatch.setattr(mobile_sources, 'additional_sources', lambda: [])
    monkeypatch.setattr(training_sources, 'sources', lambda: [])
    result = careers.run()
    assert result['updatedAt'] == previous['updatedAt']
    assert result['lastAttemptAt'] != previous['updatedAt']
    assert [c['id'] for c in result['courses']] == ['course-fundae-2']
    assert result['courses'][0]['retainedAfterFailure']
