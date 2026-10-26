from scanner.public_exams import parse


def test_official_card_keeps_actual_places_degree_and_deadline():
    html='''<div data-load-total="1"></div><div class="pag-card-convo"><div class="pag-title"><a href="/detalle?selectorget=222569">Técnico Superior de Informática</a></div>
    <div class="mb-2"><span class="dnt-txt-body-l">Ref.:</span><span>222569</span></div>
    <div class="mb-2"><span class="dnt-txt-body-l">Fin de plazo:</span><span>29/10/2026</span></div>
    <div class="mb-2"><span class="dnt-txt-body-l">Titulación:</span><span>Técnico Superior DAM</span></div>
    <div class="mb-2"><span class="dnt-txt-body-l">Ubicación:</span><span>LOCAL GALICIA A CORUÑA</span></div>
    <div class="mb-2"><span class="dnt-txt-body-l">Órgano convocante:</span><span>Ayuntamiento de Coruña, A</span></div>
    <div class="mb-2"><span class="dnt-txt-body-l">Plazas:</span>Convocadas:2 Libres:2 Internas:0</div></div>'''
    rows,total=parse(html,'2026-10-25T12:00:00Z')
    assert total==1 and rows[0]['freePlaces']==2
    assert rows[0]['fit']=='dam' and rows[0]['municipality']=='coruna'
    assert rows[0]['closingDate']=='2026-10-29'
    assert 'BOE-A-2026-20340' in rows[0]['url']
    assert parse(html,'2026-10-30T12:00:00Z')[0]==[]


def test_failure_page_is_not_an_empty_success():
    import pytest
    with pytest.raises(ValueError):parse('<h1>Error</h1>','2026-10-25T00:00:00Z')


def test_sudden_global_zero_does_not_erase_previously_open_calls(tmp_path, monkeypatch):
    import json
    from scanner import public_exams as module
    data = tmp_path / 'data'
    data.mkdir()
    call = dict(id='pag-1', closingDate='2099-01-01', checkedAt='2026-10-20T12:00:00Z')
    (data/'public-exams.json').write_text(json.dumps(dict(calls=[call])), encoding='utf-8')
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'scan', lambda now: ([], [dict(name='PAG',status='ok',examined=0)]))
    monkeypatch.setattr(module, 'check_vigo', lambda: dict(name='Vigo',status='ok',examined=0))
    result=module.run()
    assert result['calls'][0]['retainedAfterFailure']
    assert result['calls'][0]['checkedAt'] == call['checkedAt']
    assert any(s['status']=='error' for s in result['sources'])


def test_vigo_in_progress_is_not_open_for_enrolment(monkeypatch):
    from scanner import public_exams as module
    class Response:
        def __init__(self,content):self.content=content
    table=b'<table><tr><td><a href="plaza.jsp?id=1">Programador informatico</a></td><td>Turno libre</td><td>En proceso</td></tr></table>'
    monkeypatch.setattr(module,'get',lambda url:Response(table if 'ofertas_tipo' in url else b'Convocatoria fuera de plazo para presentar solicitudes.'))
    result=module.check_vigo()
    assert result['matched']==0 and result['examined']==1
