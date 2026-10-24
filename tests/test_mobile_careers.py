"""The mobile feed must not turn irrelevant results into local/remote jobs."""
from datetime import date, timedelta
from scanner import mobile_careers as careers


def test_zero_results_ignores_unrelated_latest_offers():
    html = '''No se han encontrado ofertas para los parámetros introducidos
      <table><tr><td>23/10/2026</td><td><a href="detalleOferta.do?id=123">Electricista</a></td><td>Madrid</td></tr></table>'''
    assert careers.parse_results(html) == ([], [])


def test_results_use_stable_links_without_search_session():
    html = '''Resultados de la búsqueda <table><tr><td>23/10/2026</td>
      <td><a href="detalleOferta.do?id=123&amp;idFlujo=private-session">Electricista</a></td><td>Vigo</td></tr></table>'''
    rows, _ = careers.parse_results(html)
    assert rows[0]['location'] == 'Vigo'
    assert rows[0]['url'].endswith('modo=inicio&id=123')
    assert 'idFlujo' not in rows[0]['url']


def test_geography_comes_from_location_not_title():
    meta = careers.classify_offer('Programador equipo Vigo', 'Teletrabajo con presencial en Barcelona', 'Barcelona')
    assert not meta['inVigo']
    assert meta['workplace'] == 'hybrid'
    assert careers.classify_offer('Electricista', 'Sin experiencia, formación a cargo', 'Vigo')['experience'] == 'junior'
    assert careers.classify_offer('Developer', 'No se permite teletrabajo', 'Madrid')['workplace'] != 'remote'


def test_workable_checks_employer_geography_age_and_hybrid(monkeypatch):
    def job(code, **kwargs):
        return dict(shortcode=code, title='Junior Developer', locations=[{'countryCode': 'ES', 'city': 'Madrid'}],
                    telecommuting=True, published_on=date.today().isoformat(), **kwargs)
    jobs = [job('valid'), job('hybrid', description='Teletrabajo con presencial en Madrid'),
            job('expired'), job('foreign')]
    jobs[2]['published_on'] = (date.today() - timedelta(days=181)).isoformat()
    jobs[3]['locations'] = [{'countryCode': 'US', 'city': 'Boston'}]
    class Response:
        def raise_for_status(self): pass
        def json(self): return dict(name='Example', jobs=jobs)
    monkeypatch.setattr(careers.requests, 'get', lambda *a, **kw: Response())
    offers, count = careers.workable_programming('example', 'Example', '2026-10-24T12:00:00Z')
    assert count == 4
    assert [o['id'] for o in offers] == ['career-wk-example-valid']
    assert offers[0]['sourceKind'] == 'employer'
