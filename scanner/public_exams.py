"""Read public open-access calls from the official PAG search, without a login."""
import json
import re
from datetime import datetime, timezone, date
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from scanner.mobile_careers import fold
from scanner.mobile_sources import get

ROOT = Path(__file__).resolve().parents[1]
HOST = 'https://administracion.gob.es'
SEARCH = HOST + '/empleopublico/resultados-empleo'
SERVICE = HOST + '/content/pag-home/es/empleopublico/resultados-empleo/jcr:content/root/container/containerSpace/pag_front_formulario.list.html'
QUERIES = ['informatica', 'electric', 'electronic', 'telecomunicaciones', 'mantenimiento']
VIGO='https://sede.vigo.org/expedientes/oposicions/ofertas_tipo.jsp?id=2&lang=es&tipo=1'


def check_vigo():
    """Check relevant municipal processes; never equate 'En proceso' with open enrolment."""
    soup=BeautifulSoup(get(VIGO).content,'html.parser')
    if not soup.select('tr'):raise ValueError('Vigo public call table missing')
    examined=0
    for row in soup.select('tr'):
        cells=row.find_all('td')
        if len(cells)<3:continue
        title=cells[0].get_text(' ',strip=True)
        if not re.search(r'informatic|programad|sistemas|electric|electronic|telecom',fold(title)):continue
        kind=fold(cells[1].get_text(' ',strip=True));state=fold(cells[2].get_text(' ',strip=True))
        if 'interna' in kind or 'finalizada' in state:continue
        link=cells[0].find('a',href=True)
        if not link:raise ValueError('Vigo process has no original link')
        detail=BeautifulSoup(get(urljoin(VIGO,link['href'])).content,'html.parser').get_text(' ',strip=True)
        examined+=1
        if 'fuera de plazo para presentar solicitudes' not in fold(detail):
            # Surface an actionable source warning instead of inventing an opening or a deadline.
            raise ValueError('Vigo: proceso relevante sin cierre de solicitudes confirmado; revisar sede municipal')
    return dict(name='Concello de Vigo · procesos municipales',status='ok',examined=examined,matched=0,
        note='Los procesos relacionados revisados están fuera de plazo. En proceso no significa inscripción abierta.')


def fields(card):
    out = {}
    for block in card.select('div.mb-2'):
        label = block.select_one('.dnt-txt-body-l')
        if not label:
            continue
        key = fold(label.get_text(' ', strip=True)).rstrip(':').strip()
        label.extract()
        out[key] = block.get_text(' ', strip=True)
    return out


def parse(html, now):
    soup = BeautifulSoup(html, 'html.parser')
    container = soup.select_one('[data-load-total]')
    if container is None:
        raise ValueError('PAG result layout not recognized')
    total = int(container['data-load-total'])
    cards = soup.select('.pag-card-convo')
    if total and not cards:
        raise ValueError('PAG has results but no recognized cards')
    out = []
    for card in cards:
        title_link = card.select_one('.pag-title a[href]')
        if not title_link:
            raise ValueError('PAG result missing title')
        data = fields(card)
        title = title_link.get_text(' ', strip=True)
        ref = data.get('ref.', '')
        if not ref.isdigit():
            raise ValueError('PAG reference missing')
        qualification = data.get('titulacion', '')
        text = fold(title)
        if not re.search(r'informatic|programa|electric|electronic|telecom|mantenimiento', text):
            continue
        q = fold(qualification)
        if re.search(r'universitari|licenciatur|doctorado|master|ingenieri', q) and not re.search(r'bachiller|formacion profesional|tecnic[oa].{0,10}superior|\bdam\b', q):
            continue
        raw_end = data.get('fin de plazo', '')
        end = datetime.strptime(raw_end, '%d/%m/%Y').date().isoformat() if re.fullmatch(r'\d{2}/\d{2}/\d{4}', raw_end) else None
        if end and end < now[:10]:
            continue
        location = data.get('ubicacion', '')
        body = data.get('plazas', '')
        places = re.search(r'Convocadas\s*:\s*(\d+)', body, re.I)
        free = re.search(r'Libres\s*:\s*(\d+)', body, re.I)
        if free and int(free.group(1)) == 0:
            continue
        organization = data.get('organo convocante', '')
        local = fold(location)
        area = 'national' if 'nacional' in local else 'galicia' if 'galicia' in local else 'other'
        municipality = 'vigo' if re.search(r'(?:ayuntamiento|concello) de vigo\b', fold(organization)) else 'coruna' if re.search(r'(?:ayuntamiento|concello) (?:de|da) (?:a |la )?coruna(?:,? a)?\b', fold(organization)) else None
        verified_documents = {'222569':'https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-20340'}
        out.append(dict(id='pag-'+ref, reference=ref, title=title, organization=organization,
            location=location, area=area, municipality=municipality,
            qualification=qualification, fit='dam' if re.search(r'\bdam\b|desarrollo de aplicaciones multiplataforma', q) else 'review',
            places=int(places.group(1)) if places else None, freePlaces=int(free.group(1)) if free else None,
            closingDate=end, deadlineEvidence='Fecha orientativa publicada por el PAG. Confirma las bases y posibles ampliaciones.',
            status='open' if end else 'check', source='Punto de Acceso General · Empleo público',
            url=verified_documents.get(ref, SEARCH+'?pag_referencia='+ref), pagDetailUrl=urljoin(HOST,title_link['href']), searchUrl=SEARCH+'?pag_referencia='+ref,
            access='Acceso libre (filtro del buscador oficial)', checkedAt=now))
    return out, total


def scan(now):
    rows, status = {}, []
    for query in QUERIES:
        for level in ['3', '4']:
            key = query+'-'+level
            found = set()
            try:
                for page in range(1, 21):
                    import requests
                    response = requests.get(SERVICE, params=dict(pag_viaGrupo='2', pag_tipoPlazo='1',
                        pag_nivelTitulacion=level, pag_descripcion=query, page=page),
                        headers={'User-Agent':'YagoCareerTracker/1.0'}, timeout=30)
                    response.raise_for_status()
                    parsed, total = parse(response.content, now)
                    # Pagination must advance; no fabricated successful empty scan.
                    soup = BeautifulSoup(response.content, 'html.parser')
                    refs = tuple(a.get('href') for a in soup.select('.pag-title a'))
                    if refs in found:
                        raise ValueError('PAG pagination repeated a page')
                    found.add(refs)
                    rows.update({r['id']:r for r in parsed})
                    if page*10 >= total:
                        break
                else:
                    raise ValueError('PAG search exceeds pagination limit')
                status.append(dict(name='PAG · '+key,status='ok',examined=total))
            except Exception as error:
                status.append(dict(name='PAG · '+key,status='error',reason=str(error)[:180]))
    return list(rows.values()), status


def run():
    now = datetime.now(timezone.utc).isoformat()
    path = ROOT/'data/public-exams.json'
    previous = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    rows, status = scan(now)
    old_open = [r for r in previous.get('calls', []) if (r.get('closingDate') or '') >= now[:10]]
    if not rows and old_open and all(s['status'] == 'ok' and s.get('examined') == 0 for s in status):
        # The public CDN has returned the same cached empty fragment for unrelated
        # queries. A sudden global zero is not sufficient evidence of withdrawal.
        status.append(dict(name='PAG · comprobación de coherencia', status='error',
            reason='Todas las consultas devuelven cero pese a convocatorias previas dentro de plazo. Confirmar en la fuente; se conservan sin renovar su verificación.'))
    try:status.append(check_vigo())
    except Exception as error:status.append(dict(name='Concello de Vigo · procesos municipales',status='error',reason=str(error)[:180]))
    if any(s['status']=='error' for s in status):
        ids = {r['id'] for r in rows}
        rows += [dict(r,retainedAfterFailure=True) for r in previous.get('calls',[]) if r['id'] not in ids and (r.get('closingDate') or '') >= now[:10]]
    out = dict(schemaVersion=1,lastAttemptAt=now,
        updatedAt=now if any(s['status']=='ok' for s in status) else previous.get('updatedAt'),calls=rows,sources=status,
        note='Fuente oficial informativa, cobertura parcial. No implica admisión ni destino garantizado. Las fechas del PAG son orientativas; mandan las bases oficiales.')
    temp=path.with_suffix('.json.tmp');temp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
    print(json.dumps(dict(calls=len(rows),failures=sum(s['status']=='error' for s in status))))
    return out


if __name__=='__main__':
    run()
