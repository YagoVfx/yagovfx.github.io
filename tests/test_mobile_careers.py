"""The mobile feed must not turn irrelevant results into local/remote jobs."""
from datetime import date, timedelta
from scanner import mobile_careers as careers
from scanner import mobile_sources as sources


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
    assert careers.classify_offer('Electricista', '', 'A Coruña')['inCoruna']
    assert not careers.classify_offer('Electricista', '', 'Cambre, Coruña')['inCoruna']


def test_worldwide_remote_does_not_override_explicit_country_restrictions():
    assert sources.permitted_remote('Anywhere in the World', 'Work from anywhere')
    assert sources.permitted_remote('Europe', 'Fully remote')
    assert not sources.permitted_remote('United States', 'Remote')
    assert not sources.permitted_remote('', 'Remote')
    assert not sources.permitted_remote('Anywhere in the World', 'Location: Remote-first (Argentina)')
    assert not sources.permitted_remote('Worldwide', 'Must be based in Canada')


def test_remoteok_accepts_the_api_domain_capitalization(monkeypatch):
    class Response:
        def json(self):
            return [{'legal':'API terms'}, dict(id='123', position='Junior Developer',
                company='Example', location='Worldwide', description='Work from anywhere',
                date='2026-10-23T12:00:00+00:00', url='https://remoteOK.com/remote-jobs/example')]
    monkeypatch.setattr(sources, 'get', lambda url: Response())
    assert sources.remoteok('2026-10-24T12:00:00Z')[0]['id']=='career-remoteok-123'


def test_adecco_keeps_valid_offer_when_other_seed_has_been_removed(monkeypatch):
    class Response:
        status_code = 200
        def raise_for_status(self): pass
        @property
        def content(self):
            return ('<script type="application/ld+json">' + __import__('json').dumps(dict(
                **{'@type':'JobPosting'}, title='Electricista', jobId='abc', description='Cableado y electricidad',
                validThrough='2099-01-01', datePosted='2026-10-20', jobLocation={'address':{'addressLocality':'Vigo'}})) + '</script>').encode()
    class Removed(Response): status_code = 410
    monkeypatch.setattr(sources, 'ADECCO_SEEDS', ['https://example.com/removed','https://example.com/valid'])
    monkeypatch.setattr(sources.requests, 'get', lambda url, **kw: Removed() if url.endswith('removed') else Response())
    rows = sources.adecco('2026-10-24T12:00:00Z')
    assert len(rows) == 1
    assert rows[0]['inVigo'] and rows[0]['category']=='electricity'


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
