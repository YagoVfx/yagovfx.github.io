import json
from bs4 import BeautifulSoup
from scanner import radar_sources as radar
from scanner import training_sources as training
from scanner import stratos_source as stratos
import pytest


NOW='2026-10-24T12:00:00Z'


class Response:
    status_code=200
    def __init__(self,data=None,text=''):
        self.data=data;self.text=text;self.content=text.encode()
    def json(self):return self.data


def test_stratos_only_current_employment_vfx_not_collaborations(monkeypatch):
    feed='''<rss><channel><title>Stratos</title>
      <item><title>Studio busca VFX Artist</title><category>Trabajo</category><link>https://stratos-ad.com/trabajo?job=123</link><pubDate>23 Oct 2026 12:00:00 +0100</pubDate><description>Tipo de contrato: Autónomo/freelance Texto de la oferta: Niagara</description></item>
      <item><title>VFX colaboración</title><category>Colaboración</category><link>https://stratos-ad.com/colaboracion?collaboration=999</link></item>
      <item><title>Studio busca VFX Artist</title><category>Trabajo</category><link>https://stratos-ad.com/trabajo?job=124</link><pubDate>01 Jan 2025 12:00:00 +0100</pubDate></item>
    </channel></rss>'''
    listing='<h2>Trabajo</h2><table><tr><td>23/10/2026</td><td><a href="/trabajo?job=123">VFX Artist</a></td><td>Remoto (España)</td><td>Studio</td></tr></table>'
    monkeypatch.setattr(stratos,'public_response',lambda url:Response(text=feed if url==stratos.RSS else listing))
    rows=stratos.read(NOW)
    assert [r['id'] for r in rows]==['career-stratos-123']
    assert rows[0]['workplace']=='remote'
    assert rows[0]['company']=='Studio'
    assert rows[0]['description']=='Niagara'
    assert any('freelance' in r for r in rows[0]['requirements'])


def test_stratos_challenge_or_login_page_is_not_treated_as_an_empty_feed(monkeypatch):
    monkeypatch.setattr(stratos,'public_response',lambda url:Response(text='<html>Access denied</html>'))
    with pytest.raises(ValueError,match='RSS'):stratos.read(NOW)


def test_gamesjobs_invalid_address_punctuation_is_read_without_eval():
    soup=BeautifulSoup('''<script type="application/ld+json">{
      "@type":"JobPosting","title":"VFX Artist",
      "jobLocation":{"address":{"addressRegion":"Sweden";"addressCountry":"Sweden";}}
    }</script>''','html.parser')
    assert radar.jobposting(soup)['jobLocation']['address']['addressCountry']=='Sweden'
    assert radar.vfx_role('Senior Technical Artist')
    assert not radar.vfx_role('Marketing Artist')


def test_inditex_imports_specific_roles_not_talent_pools(monkeypatch):
    def offer(id,title):return dict(id=id,title=title,city='A CORUÑA',careers_url='https://zara.recruitee.com/o/'+str(id),description='Java software',requirements='Experiencia')
    monkeypatch.setattr(radar,'get',lambda url:Response({'offers':[offer(1,'SENIOR PRODUCT ENGINEER'),offer(2,'INDITEX TECH, JOIN US!'),offer(3,'COMPRADOR TEJIDOS')]}))
    rows=radar.inditex(NOW)
    assert [x['id'] for x in rows]==['career-inditex-1']
    assert rows[0]['inCoruna']


def test_hidden_closed_banner_does_not_close_an_active_indie_job(monkeypatch):
    rss='<rss><channel><item><title>Studio is hiring a VFX Artist to work from Anywhere</title><link>https://www.workwithindies.com/careers/studio-vfx</link></item></channel></rss>'
    posting={'@type':'JobPosting','title':'VFX Artist','hiringOrganization':{'name':'Studio'},'description':'Unreal effects','jobLocationType':'TELECOMMUTE'}
    def page(hidden):return '<div class="closed-notif '+('w-condition-invisible' if hidden else '')+'">This position has been closed.</div><script type="application/ld+json">'+json.dumps(posting)+'</script>'
    monkeypatch.setattr(radar,'get',lambda url:Response(text=rss if url.endswith('.xml') else page(True)))
    assert len(radar.workwithindies(NOW))==1
    monkeypatch.setattr(radar,'get',lambda url:Response(text=rss if url.endswith('.xml') else page(False)))
    assert radar.workwithindies(NOW)==[]


def test_veolia_does_not_turn_province_metadata_into_a_city_job(monkeypatch):
    rows=[dict(id='1',name='Electricista',location={'city':'La Coruña'},ref='https://example.com/1',releasedDate='2026-10-23'),
          dict(id='2',name='Jefe de obra instalaciones eléctricas Bergondo',location={'city':'A Coruña'},ref='https://example.com/2')]
    def get(url):
        if 'postings?' in url:return Response({'content':rows,'totalFound':2})
        assert url.endswith('/1')
        return Response({'active':True,'jobAd':{'sections':{'description':{'text':'Mantenimiento eléctrico y cableado'}}}})
    monkeypatch.setattr(radar,'get',get)
    found=radar.veolia(NOW)
    assert [r['id'] for r in found]==['career-veolia-1']
    assert found[0]['category']=='electricity'


def test_diplos_real_location_online_and_start_date(monkeypatch):
    def course(id,city,mode,start='01/12/2026'):
        return dict(codigo='ELEE001',denominacion='Electricidad de circuitos',nivelProfesionalId='1',
                    accionFormativaItem=dict(accionFormativaId=id,municipio=city,modalidad=mode,fechaInicio=start,fechaFin='31/01/2027',horasCurso='70'))
    data=[course('2026/1','VIGO','010'),course('2026/2','SANTIAGO','010'),course('2026/3','OURENSE','006'),course('2026/4','VIGO','010','01/09/2026')]
    monkeypatch.setattr(training,'get',lambda url:Response({'listItems':data if 'familia=ELE' in url else [],'totalItems':len(data) if 'familia=ELE' in url else 0}))
    rows=training.diplos(NOW)
    assert {r['id'] for r in rows}=={'course-diplos-2026-1','course-diplos-2026-3'}
    assert rows[0]['durationHours']==70
    assert rows[0]['enrollmentStatus']=='consult'  # planning is not proof of open places
    assert training.topic_for('Animación 3D','IMS123')=='vfx'
    assert training.topic_for('Programación Java','IFC123')=='programming'


def test_cntg_only_open_online_courses_and_no_presential_santiago(monkeypatch):
    def row(id,mode,deadline):return f'<tr><td><a href="/gl/curso/{id}/java">Java</a></td><td>Curso</td><td>01/12/2026</td><td>01/10/2026</td><td>{deadline}</td><td>{mode}</td><td>Si</td></tr>'
    listing='<table class="views-table"><tbody>'+row('ok','Virtual','08/11/2026')+row('closed','Virtual','01/10/2026')+row('onsite','Presencial','08/11/2026')+'</tbody></table>'
    monkeypatch.setattr(training,'get',lambda url:Response(text=listing if 'buscar-cursos?' in url else '<article>Curso Java 40 horas. Requisitos: programación básica.</article>'))
    rows=training.cntg(NOW)
    assert [r['id'] for r in rows]==['course-cntg-ok']
    assert rows[0]['enrollmentStatus']=='open'
