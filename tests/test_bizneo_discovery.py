from scanner import bizneo_sources as source


def test_separate_city_field_is_used_and_requirements_are_not_truncated(monkeypatch):
    class Response:
        def __init__(self,html):self.content=html.encode()
    listing='''<a class="job-card" href="/jobs/junior"><div class="title">Junior Java Developer</div>
    <div class="details"><span class="aggregation">Técnico</span><span>Vigo</span><span>Híbrido</span></div></a>'''
    detail='<main><h1>Junior Java Developer</h1>'+('Descripción. '*500)+'Requisitos mínimos: Formación Profesional DAM.</main>'
    monkeypatch.setattr(source,'get',lambda url:Response(listing if url.endswith('/jobs') else detail))
    rows=source.read_board('https://company.test','Company','company','2026-10-26T12:00:00Z')
    assert len(rows)==1 and rows[0]['inVigo']
    assert rows[0]['workplace']=='hybrid'
    assert 'Formación Profesional DAM' in rows[0]['description']
    assert rows[0]['postedDate'] is None
