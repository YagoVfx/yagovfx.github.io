import pytest
from scanner import training_sources as training
from scanner.mobile_careers import classify_offer, parse_results


@pytest.mark.parametrize('title,code,expected', [
    ('ChatGPT e intelixencia artificial', 'IFC123', 'digital'),
    ('ANÁLISE DE DATOS CON EXCEL: POWER QUERY', 'IFC123', 'digital'),
    ('COMPETENCIAS DIXITAIS AVANZADAS', 'IFC123', 'digital'),
    ('Programación Java', 'IFC123', 'programming'),
    ('MF0950: Construción de páxinas web', 'IFC123', 'programming'),
    ('Montaxe de sistemas de telefonía', 'ELES0209', 'telecom'),
    ('Sistemas microinformáticos', 'IFC123', 'telecom'),
    ('Electricidad', 'ELE123', 'electricity'),
    ('Animación 3D', 'IMS123', 'vfx'),
    ('Curso sin especialidad reconocible', 'IFC123', None),
])
def test_course_specialty_comes_from_content_not_just_it_family(title, code, expected):
    assert training.topic_for(title, code) == expected


def test_sne_actual_municipal_alias_with_province():
    assert classify_offer('Electricista', '', 'Coruña, a (Coruña (a))')['inCoruna']
    with pytest.raises(RuntimeError):
        parse_results('Resultados de la búsqueda <div>Unexpected layout</div>')


def test_diplos_does_not_assume_fifty_records_per_page(monkeypatch):
    class Response:
        def __init__(self, rows, total): self.rows, self.total = rows, total
        def json(self): return dict(listItems=self.rows, totalItems=self.total)
    def course(code):
        return dict(codigo=code, denominacion='Electricidad', accionesFormativasGrupo=[])
    urls = []
    def get(url):
        urls.append(url)
        if 'familia=ELE' not in url: return Response([], 0)
        return Response([course('ELE1')] if 'pag=1' in url else [course('ELE2')], 2)
    monkeypatch.setattr(training, 'get', get)
    training.diplos('2026-10-26T12:00:00Z')
    assert any('familia=ELE&pag=2' in u for u in urls)
    monkeypatch.setattr(training, 'get', lambda url: Response([course('ELE1')], 2))
    with pytest.raises(ValueError, match='did not advance'):
        training.diplos('2026-10-26T12:00:00Z')


def test_pending_integrations_do_not_claim_transient_network_failure():
    from scanner.source_errors import IntegrationPending
    from scanner.radar_sources import artstation, xunta_employment
    for reader in (artstation, xunta_employment):
        with pytest.raises(IntegrationPending): reader('2026-10-26T12:00:00Z')
