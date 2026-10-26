"""Xunta public training catalogues. No enrolment or private student data."""
import re
import json
from datetime import datetime
from urllib.parse import urlencode, quote, urljoin

from bs4 import BeautifulSoup

from scanner.mobile_sources import get, clean
from scanner.mobile_careers import classify_offer, fold


def iso(value):
    return datetime.strptime(value, '%d/%m/%Y').date().isoformat() if value else None


def topic_for(title, code=''):
    text=fold(title)
    if re.search(r'animac|videoj|\bvfx\b|unreal|niagara|blender|houdini|3d|unity',text):return 'vfx'
    if code.startswith('ELES') or re.search(r'telecom|antenas|fibra optica|microinformatic',text):return 'telecom'
    if code.startswith('ELE') or re.search(r'electric|fotovolta|electromecanic|automatiz|domotic|electrotecn|alumbrado|cablead',text):return 'electricity'
    if re.search(r'excel|power bi|power query|power pivot|chatgpt|competencias (?:dixitais|digitales)|(?:artificial|artificia).{0,20}(?:empresa|negocio)',text):return 'digital'
    if re.search(r'programa|desenvolvement|desarrollo|python|\bjava\b|javascript|ciberseg|software|bases de datos|linux|redes|github|cloud|aws|azure|paxinas web|paginas web|algoritm',text):return 'programming'
    if re.search(r'intelixencia artificial|inteligencia artificial|big data',text):return 'digital'
    return None


def diplos(now):
    out={}
    # Family filters are official API parameters. Query all locations and then accept
    # only Vigo/A Coruña or teletraining, not other municipalities in the provinces.
    for family in ['ELE','IFC','IMS','IMA']:
        seen = set()
        examined = 0
        for page in range(1,9):
            url='https://diplos.xunta.gal/diplos/api/search?'+urlencode(dict(familia=family,pag=page))
            data=get(url).json()
            if not isinstance(data.get('listItems'),list) or 'totalItems' not in data:raise ValueError('DIPLOS API layout changed')
            signature = json.dumps(data['listItems'], sort_keys=True)
            if int(data['totalItems']) > examined and (not data['listItems'] or signature in seen):
                raise ValueError('DIPLOS pagination did not advance for '+family)
            seen.add(signature)
            examined += len(data['listItems'])
            for raw in data['listItems']:
                title=raw['denominacion'];topic=topic_for(title,raw['codigo'])
                if not topic:continue
                actions=raw.get('accionesFormativasGrupo') or []
                if raw.get('accionFormativaItem'):actions=[raw['accionFormativaItem'],*actions]
                for action in actions:
                    if not action.get('accionFormativaId'):continue
                    place=action.get('municipio') or ''
                    meta=classify_offer('', '',place)
                    online=action.get('modalidad')=='006' or action.get('exclusivoTeleformacion') is True
                    # Mixed courses are not assumed to be distance-compatible.
                    if not online and not(meta['inVigo'] or meta['inCoruna']):continue
                    start=iso(action.get('fechaInicio'))
                    end=iso(action.get('fechaFin'))
                    if end and end < now[:10] or start and start < now[:10]:continue
                    code=action['accionFormativaId'];level=raw.get('nivelProfesionalId') or ''
                    description=f"Especialidad {raw['codigo']}. {raw.get('familia','')} / {raw.get('area','')}. Nivel de acceso: {raw.get('nivelProfesional','Consultar')}. Confirmar situación laboral, matrícula, plazas y horario en el centro."
                    out[code]=dict(id='course-diplos-'+code.replace('/','-'),kind='course',title=title,
                        provider=action.get('centroRazonSocial') or 'Xunta / DIPLOS',source='Xunta / DIPLOS',topic=topic,
                        url='https://diplos.xunta.gal/diplos/curso?'+urlencode(dict(accion=code)),sourceUrl=url,
                        price=0,priceEvidence='Formación del catálogo subvencionado de Xunta / DIPLOS; confirmar condiciones en la convocatoria',
                        modality='online' if online else 'onsite',location=place,inVigo=meta['inVigo'],inCoruna=meta['inCoruna'],
                        level='beginner' if level=='1' or re.search(r'fundament|circuitos de corriente',fold(title)) else 'advanced' if level in ['3','4','5'] else 'review',
                        description=description,durationHours=int(float(action.get('horasCurso') or 0)) or None,
                        startDate=start,endDate=end,enrollmentStatus='consult',
                        availability='Curso planificado: confirmar inscripción, requisitos y plazas en DIPLOS',
                        qualification=raw.get('nivelProfesional') or 'Consultar requisitos de acceso',
                        syllabusUrl=raw.get('programaFormativoPDFUrl'),checkedAt=now)
            if examined >= int(data['totalItems']):break
        else:raise ValueError('DIPLOS pagination incomplete for '+family)
    return list(out.values())


def cntg(now):
    host='https://cntg.xunta.gal'
    out={}
    for page in range(0,10):
        url=host+'/gl/actividades/buscar-cursos?'+urlencode(dict(field_plazo_abierto_value=1,page=page))
        soup=BeautifulSoup(get(url).content,'html.parser')
        table=soup.select_one('table.views-table')
        if not table:raise ValueError('CNTG course table missing')
        rows=table.select('tbody tr')
        for tr in rows:
            cells=tr.select('td')
            if len(cells)!=7:raise ValueError('CNTG table columns changed')
            a=cells[0].select_one('a[href]')
            if not a:continue
            title=a.get_text(' ',strip=True);topic=topic_for(title)
            if not topic:continue
            start=iso(cells[2].get_text(' ',strip=True));enrol_start=iso(cells[3].get_text(' ',strip=True));deadline=iso(cells[4].get_text(' ',strip=True))
            if deadline and deadline < now[:10]:continue
            mode=fold(cells[5].get_text(' ',strip=True))
            if 'presencial' in mode:continue  # CNTG's physical campus is Santiago, not Vigo/A Coruña.
            if not ('virtual' in mode or 'teleformacion' in mode):continue
            link=urljoin(host,a['href']);detail=BeautifulSoup(get(link).content,'html.parser')
            article=detail.select_one('article') or detail.select_one('main')
            if not article:raise ValueError('CNTG detail missing')
            description=article.get_text(' ',strip=True)
            hours=re.search(r'(\d+)\s*(?:horas|h\b)',description,re.I)
            code=link.split('/curso/',1)[1].split('/')[0]
            out[code]=dict(id='course-cntg-'+code,kind='course',title=title,provider='CNTG · Xunta de Galicia',source='CNTG',topic=topic,
                url=link,sourceUrl=url,price=0,modality='online',location='',level='beginner' if re.search('introdu|fundament|restart',fold(title)) else 'review',
                description=description[:4500],durationHours=int(hours.group(1)) if hours else None,startDate=start,
                enrollmentStart=enrol_start,enrollmentEnd=deadline,enrollmentStatus='open' if enrol_start and enrol_start<=now[:10] and deadline and deadline>=now[:10] else 'consult',
                availability='Inscripción hasta '+deadline+'; confirmar plazas y proceso de selección' if deadline else 'Consultar inscripción',
                qualification='Revisar conocimientos previos, situación laboral, selección y horario de aula virtual',
                certificate='La ficha indica certificación; confirmar examen, asistencia y condiciones' if fold(cells[6].get_text(strip=True))=='si' else 'No confirmada',
                checkedAt=now)
        if not soup.select_one('li.pager__item--next a'):break
    else:raise ValueError('CNTG pagination incomplete')
    return list(out.values())


def sources():
    from scanner.paid_training import sources as paid_sources
    return [('diplos','Xunta / DIPLOS · formación',diplos),('cntg','CNTG · inscripción abierta',cntg),('sidefx','SideFX · videojuegos y VFX',sidefx),*paid_sources()]


def sidefx(now):
    """Selected original lessons; recheck the public page every scan."""
    lessons = [
        ('fluid-fx-for-realtime', 'Fluid FX for Realtime', 'intermediate', 153, 'improve'),
        ('realtime-destruction-techniques', 'Realtime Destruction Techniques', 'intermediate', 104, 'improve'),
        ('how-to-export-to-pcg-in-unreal', 'How to Export to PCG in Unreal', 'intermediate', 51, 'new'),
        ('foundations-procedural-assets-for-unreal', 'Procedural Assets for Unreal', 'beginner', 40, 'new'),
    ]
    out = []
    for slug, title, level, minutes, goal in lessons:
        url = 'https://www.sidefx.com/tutorials/' + slug + '/'
        soup = BeautifulSoup(get(url).content, 'html.parser')
        heading = soup.find('h1')
        if not heading or fold(title) not in fold(heading.get_text(' ', strip=True)):
            raise ValueError('SideFX lesson title changed: ' + slug)
        out.append(dict(id='course-sidefx-'+slug, kind='tutorial', title=title,
            provider='SideFX', source='SideFX', topic='vfx', url=url, sourceUrl=url,
            price=0, modality='online', level=level, learningGoal=goal,
            durationHours=round(minutes/60,2), checkedAt=now,
            description='Lección práctica de VFX y Technical Art para Unreal/Houdini. Consultar conocimientos previos, versión y archivos en la página original.',
            qualification='Conocimientos de Houdini y Unreal según la lección. Revisar licencias: acceso gratuito al tutorial no incluye licencias de software.',
            availability='Autoaprendizaje con vídeos públicos. Sin plazas ni certificado profesional confirmados.'))
    return out
