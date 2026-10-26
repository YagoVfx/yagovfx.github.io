"""Additional mobile-only careers. Public employment service != employer ATS.

Uses the same public search forms as SNE visitors, without login or API secrets.
Does not change the VFX feed or publish the user's education/profile.
"""
import json
import logging
import re
import time
import unicodedata
from datetime import datetime, timezone, date
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
from scanner.source_errors import IntegrationPending

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.sistemanacionalempleo.es/OfertaDifusionWEB/'
HEADERS = {'User-Agent': 'YagoCareerTracker/1.0 (personal public employment reader)'}
LOG = logging.getLogger(__name__)


def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.lower()) if unicodedata.category(c) != 'Mn')


def role_category(title):
    text = fold(title)
    if re.search(r'\b(programad|desarrollad|software|developer|tester|qa\b|testing|backend|frontend|full.?stack|growth engineer)', text):
        return 'programming'
    if re.search(r'electric|electromecanic|fotovoltaic|instalador|mantenimiento', text):
        # A generic maintenance title must be verified against its description later.
        return 'electricity'
    return None


def classify_offer(title, description, location):
    text = fold(title + ' ' + description)
    advanced = bool(re.search(r'\b(senior|lead|principal|jefe)\b|oficial.{0,8}(primera|1[ªaº])', fold(title)) or re.search(r'(?:minim[oa]|al menos|at least|minimum).{0,25}[3-9]\+?\s*(?:anos|years)', text))
    junior = bool(re.search(r'\bjunior\b|trainee|entry.level', fold(title)) or re.search(r'sin experiencia|no.{0,15}(necesaria|requiere).{0,12}experiencia|formacion a cargo', text))
    hybrid = bool(re.search(r'hibrid|teletrabajo.{0,25}(parcial|dias)|presencial.{0,25}teletrabajo|teletrabajo.{0,40}presencial', text))
    remote = not hybrid and bool(re.search(r'teletrabajo|en remoto|100\s*%.{0,15}remoto|fully remote', text))
    if re.search(r'no (?:se )?(?:ofrece|permite|admite).{0,12}teletrabajo|sin teletrabajo', text):
        remote = False
    flags = []
    if re.search(r'prl|prevencion de riesgos', text): flags.append('Revisar formación PRL requerida')
    if re.search(r'carn[eé]t|permiso de conducir', text): flags.append('Revisar permiso de conducir')
    if re.search(r'desplaz|viajar|movilidad', text): flags.append('Revisar desplazamientos y viajes')
    if re.search(r'ingenier|grado universitario', text): flags.append('Revisar si exige titulación universitaria')
    if re.search(r'\d\+?\s*(?:anos|years).{0,15}experien|experien.{0,20}\d\+?\s*(?:anos|years)', text): flags.append('Revisar años de experiencia exigidos')
    location_text = fold(location).strip()
    location_text = re.sub(r'^coruna,\s*a(?=\s*(?:\(|,|$))', 'a coruna', location_text)
    location_text = re.sub(r'^(?:teis|bouzas|zona franca|pol\.?\s*ind\.?\s*balaidos)\s*(?:,\s*|\()vigo\)?(?=,|$)', 'vigo', location_text)
    city = re.split(r'[,;/|]|\s+[-–]\s+', location_text)[0].strip()
    city = re.sub(r'^municipio de\s+', '', city)
    in_vigo = bool(re.fullmatch(r'vigo(?:\s*\([^)]*\))?', city))
    in_coruna = bool(re.fullmatch(r'(?:a coruna|la coruna)(?:\s*\(.*\))?|coruna\s*\(a\)', city))
    nearby = r'\b(?:arteixo|cambre|culleredo|oleiros|bergondo|betanzos|carballo|sada|redondela|porrino|nigran|gondomar|moana|cangas|mos|ponteareas)\b'
    if re.search(nearby, fold(title)):
        in_vigo = in_coruna = False
    return dict(experience='experienced' if advanced else 'junior' if junior else 'unknown',
                workplace='hybrid' if hybrid else 'remote' if remote else 'unknown',
                inVigo=in_vigo, inCoruna=in_coruna, requirements=flags)


def parse_results(html):
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(' ', strip=True)
    # On zero matches SNE redisplays the form AND unrelated "latest offers".
    # Never import those unrelated rows as search results.
    if 'No se han encontrado ofertas para los parámetros introducidos' in text:
        return [], []
    if 'Resultados de la búsqueda' not in text:
        raise RuntimeError('SNE search result layout not recognized')
    rows = []
    for anchor in soup.select('a[href*="detalleOferta.do"]'):
        query = parse_qs(urlparse(anchor['href']).query)
        identifier = (query.get('id') or [''])[0]
        if not identifier.isdigit(): continue
        cells = anchor.find_parent('tr').find_all('td', recursive=False)
        if len(cells) != 3: raise RuntimeError('SNE result columns changed')
        rows.append(dict(sourceId=identifier, title=anchor.get_text(' ', strip=True),
                         location=cells[2].get_text(' ', strip=True), postedDate=cells[0].get_text(' ', strip=True),
                         url=BASE + 'detalleOferta.do?modo=inicio&id=' + identifier))
    pages = [urljoin(BASE, a['href']) for a in soup.select('a[href*="listadoOfertas.do"]')
             if 'indice=' in a['href']]
    if not rows:
        raise RuntimeError('SNE results have no recognized rows or explicit empty-result message')
    return rows, pages


class SneSearch:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get(self, url):
        response = self.session.get(url, timeout=25)
        response.raise_for_status()
        return response.text

    def search(self, term, local=False):
        html = self.get(BASE + 'busquedaOfertas.do?modo=inicio')
        soup = BeautifulSoup(html, 'html.parser')
        flow = soup.select_one('input[name=idFlujo]')['value']
        data = dict(idFlujo=flow, palabraBusqueda=term, sectorProfesional='', botonNavegacion='Enviar')
        if local:
            self.get(BASE + 'busquedaOfertas.do?modo=cambiarModo&idFlujo=' + flow)
            province, municipality = ('15', '15030') if local == 'coruna' else ('36', '36057')
            data.update(provincia=province, municipio='', botonNavegacion='Filtrar municipios')
            response = self.session.post(BASE + 'busquedaOfertas.do?modo=continuar', data=data, timeout=25)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            options = {o.get('value'): o.get_text(' ', strip=True) for o in soup.select('select[name=municipio] option')}
            if municipality not in options: raise RuntimeError('SNE municipality filter not recognized')
            data.update(idFlujo=soup.select_one('input[name=idFlujo]')['value'], municipio=municipality, botonNavegacion='Enviar')
        response = self.session.post(BASE + 'busquedaOfertas.do?modo=continuar', data=data, timeout=25)
        response.raise_for_status()
        rows, pages = parse_results(response.text)
        seen_pages = set()
        while pages:
            page = pages.pop(0)
            if page in seen_pages: continue
            if len(seen_pages) >= 8: raise RuntimeError('SNE search exceeds pagination limit; incomplete result')
            seen_pages.add(page)
            more, extra = parse_results(self.get(page))
            rows.extend(more); pages.extend(p for p in extra if p not in seen_pages)
            time.sleep(.15)
        return {row['sourceId']: row for row in rows}.values()

    def detail(self, row):
        soup = BeautifulSoup(self.get(row['url']), 'html.parser')
        text = soup.get_text(' ', strip=True)
        if row['sourceId'] not in text or 'Datos adicionales' not in text:
            raise RuntimeError('SNE offer detail not recognized')
        description = text.split('Datos adicionales', 1)[1].split('Datos de contacto', 1)[0].strip()
        end_match = re.search(r'Fecha de fin:\s*(\d{2}/\d{2}/\d{4})', text)
        expires = datetime.strptime(end_match.group(1), '%d/%m/%Y').date() if end_match else None
        if expires and expires < date.today(): return None
        category = role_category(row['title'])
        if category == 'electricity' and not re.search(r'electric|electromecanic|fotovoltaic|alumbrado|cablead|cuadros electric', fold(description)):
            return None
        if not category: return None
        meta = classify_offer(row['title'], description, row['location'])
        if category == 'electricity' and not (meta['inVigo'] or meta['inCoruna']): return None
        if category == 'programming' and not (meta['inVigo'] or meta['inCoruna']) and meta['workplace'] != 'remote': return None
        return dict(id='career-sne-' + row['sourceId'], category=category, title=row['title'],
                    company='Empresa no indicada (SNE)', location=row['location'], url=row['url'],
                    source='Sistema Nacional de Empleo', sourceKind='public-employment-service',
                    description=description[:16000], postedDate=datetime.strptime(row['postedDate'], '%d/%m/%Y').date().isoformat(),
                    closingDate=expires.isoformat() if expires else None, **meta)


def fundae_courses():
    session = requests.Session(); session.headers.update(HEADERS)
    out = {}
    for term in ['programación', 'electricidad', 'microcontroladores']:
        response = session.get('https://www.efundae.es/course/search.php', params={'search': term}, timeout=25)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for box in soup.select('.coursebox'):
            anchor = box.select_one('a[href*="/course/view.php?id="]')
            if not anchor: continue
            title = anchor.get_text(' ', strip=True)
            text = fold(title)
            if 'formadores' in text: continue
            if not re.search('programacion|backend|frontend|microcontrolador|python|electric|automatiza|arduino|web|gemelos digitales', text): continue
            identifier = parse_qs(urlparse(anchor['href']).query)['id'][0]
            out[identifier] = dict(id='course-fundae-' + identifier, kind='course', title=title,
                provider='eFundae', topic='electricity' if re.search('electric|automatiza|microcontrol|arduino', text) else 'programming',
                url=anchor['href'], sourceUrl=response.url, price=0, modality='online', location='',
                level='advanced' if re.search(r'nivel [56]|avanzad', text) else 'review',
                description=box.get_text(' ', strip=True)[:1200], availability='Consultar acceso e inscripción en eFundae')
    return list(out.values())


def workable_programming(slug, expected_name, now):
    url = f'https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true'
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status(); data = response.json()
    if data.get('name', '').casefold() != expected_name.casefold() or not isinstance(data.get('jobs'), list):
        raise RuntimeError('Employer identity or Workable feed schema changed')
    offers = []
    for raw in data['jobs']:
        if role_category(raw.get('title', '')) != 'programming': continue
        locations = raw.get('locations') or [dict(country=raw.get('country'), city=raw.get('city'))]
        spanish = [loc for loc in locations if loc.get('countryCode') == 'ES' or loc.get('country') == 'Spain']
        if not spanish: continue
        location = ', '.join(dict.fromkeys(loc.get('city') or 'Spain' for loc in spanish))
        if not raw.get('telecommuting') and not re.search(r'\b(?:vigo|a coruna|la coruna)\b', fold(location)): continue
        published = (raw.get('published_on') or '')[:10]
        if published:
            published_date = date.fromisoformat(published)
            if (date.today() - published_date).days > 180: continue
        description = BeautifulSoup(raw.get('description') or '', 'html.parser').get_text(' ', strip=True)
        meta = classify_offer(raw['title'], description, location)
        if raw.get('telecommuting') and meta['workplace'] != 'hybrid': meta['workplace'] = 'remote'
        if not (meta['inVigo'] or meta['inCoruna']) and meta['workplace'] != 'remote': continue
        if fold(raw.get('experience') or '') in ['senior', 'mid-senior level', 'director', 'executive']: meta['experience'] = 'experienced'
        if fold(raw.get('experience') or '') in ['entry level', 'internship']: meta['experience'] = 'junior'
        education = fold(raw.get('education') or '')
        if 'master' in education or 'bachelor' in education: meta['requirements'].append('Revisar titulación universitaria requerida')
        if raw.get('employment_type') == 'Contract': meta['requirements'].append('Contrato o colaboración: confirmar si es empleo asalariado')
        offers.append(dict(id=f"career-wk-{slug}-{raw['shortcode']}", category='programming',
            title=raw['title'], company=expected_name, location=location + ', Spain',
            url=f"https://apply.workable.com/{slug}/j/{raw['shortcode']}/", source=expected_name + ' · Workable',
            sourceKind='employer', description=description[:16000], postedDate=published,
            closingDate=None, checkedAt=now, **meta))
    return offers, len(data['jobs'])


def course_available(course, today):
    """Keep ongoing open-enrolment resources; reject dated closed intakes."""
    end = course.get('enrollmentEnd') or course.get('endDate')
    if end and str(end)[:10] < today:
        return False
    start = course.get('startDate')
    return not (start and str(start)[:10] < today and not course.get('enrollmentEnd')
                and course.get('enrollmentStatus') not in ('open', 'continuous'))


def run():
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    target = ROOT / 'data/mobile-careers.json'
    previous = json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
    offers = {}; status = []; seen = set(); failures = False
    # Explicitly local electrical work; local and remote software work.
    queries = [('electricista', True), ('mantenimiento', True), ('instalador', True),
               ('electromecánico', True), ('programador', True), ('desarrollador', True),
               ('teletrabajo', False), ('remoto', False)]
    queries += [(term, 'coruna') for term in ['electricista', 'mantenimiento', 'instalador', 'electromecánico', 'programador', 'desarrollador']]
    for term, local in queries:
        search = SneSearch()  # SNE keeps basic/advanced search mode in its session.
        key = term + (' · A Coruña' if local == 'coruna' else ' · Vigo' if local else ' · nacional')
        try:
            rows = list(search.search(term, local))
            detail_failures = 0
            for row in rows:
                if row['sourceId'] in seen: continue
                seen.add(row['sourceId'])
                if not role_category(row['title']): continue
                try:
                    offer = search.detail(row)
                    if offer: offers[offer['id']] = dict(offer, checkedAt=now)
                except Exception:
                    failures = True
                    detail_failures += 1
            status.append(dict(name='SNE: ' + key, status='error' if detail_failures else 'ok', examined=len(rows),
                               **({'reason': f'{detail_failures} detalles no disponibles; consulta parcial'} if detail_failures else {})))
        except Exception as e:
            failures = True; status.append(dict(name='SNE: ' + key, status='error', reason=str(e)[:180]))
        finally:
            search.session.close()
        LOG.info('%s: %s', key, status[-1]['status'])
    # A failed scan never upgrades an old offer to freshly verified.
    if failures:
        for old in previous.get('offers', []):
            if old['id'].startswith('career-sne-') and old['id'] not in offers and (not old.get('closingDate') or old['closingDate'] >= now[:10]):
                offers[old['id']] = dict(old, retainedAfterFailure=True)
    for slug, employer in [('plainconcepts', 'Plain Concepts'), ('fabulousco', 'Fabulous'), ('european-dynamics', 'EUROPEAN DYNAMICS')]:
        try:
            rows, total = workable_programming(slug, employer, now)
            offers.update({row['id']: row for row in rows})
            status.append(dict(name=employer + ' · Workable', status='ok', examined=total))
        except Exception as e:
            status.append(dict(name=employer + ' · Workable', status='error', reason=str(e)[:180]))
            prefix='career-wk-' + slug + '-'
            for old in previous.get('offers', []):
                if old['id'].startswith(prefix) and old['id'] not in offers: offers[old['id']]=dict(old,retainedAfterFailure=True)
    from scanner.mobile_sources import additional_sources
    for key, label, reader in additional_sources():
        prefix = 'career-' + key + '-'
        try:
            LOG.info('Consultando %s', label)
            rows = reader(now)
            offers.update({row['id']: row for row in rows})
            status.append(dict(name=label, status='ok', matched=len(rows)))
        except Exception as e:
            status.append(dict(name=label, status='pending' if isinstance(e, IntegrationPending) else 'error', reason=str(e)[:180]))
            for old in previous.get('offers', []):
                if any(str(identity).startswith(prefix) for identity in [old['id'], *old.get('sourceIds', [])]) and (not old.get('closingDate') or old['closingDate'] >= now[:10]):
                    offers.setdefault(old['id'], dict(old, retainedAfterFailure=True))
    try:
        courses = fundae_courses()
        if not courses: raise RuntimeError('eFundae course search has no recognized course cards')
        courses = [dict(c, checkedAt=now) for c in courses]
        status.append(dict(name='eFundae', status='ok', examined=len(courses)))
    except Exception as e:
        courses = [dict(c, retainedAfterFailure=True) for c in previous.get('courses', []) if c['id'].startswith('course-fundae-')]
        status.append(dict(name='eFundae', status='error', reason=str(e)[:180]))
    from scanner.training_sources import sources as training_sources
    course_map = {c['id']: c for c in courses}
    for key, label, reader in training_sources():
        try:
            LOG.info('Consultando %s', label)
            rows = reader(now)
            course_map.update({row['id']: row for row in rows})
            status.append(dict(name=label, status='ok', examined=len(rows)))
        except Exception as e:
            status.append(dict(name=label,status='error',reason=str(e)[:180]))
            for old in previous.get('courses',[]):
                if old['id'].startswith('course-'+key+'-'):
                    course_map.setdefault(old['id'],dict(old,retainedAfterFailure=True))
    courses = [c for c in course_map.values() if course_available(c, now[:10])]
    from scanner.career_metadata import enrich_sources
    from scanner.vacancy_identity import unify
    direct_path = ROOT / 'data/jobs.json'
    direct = json.loads(direct_path.read_text(encoding='utf-8'))
    unique_offers = unify(list(offers.values()), direct['jobs'])
    from scanner.profile_match import profile_match
    for row in unique_offers:row.update(profile_match(row))
    direct_temporary = direct_path.with_suffix('.json.tmp')
    direct_temporary.write_text(json.dumps(direct, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    direct_temporary.replace(direct_path)
    successful = any(s['status'] == 'ok' for s in status)
    old_sources = {s['name']: s for s in previous.get('sources', [])}
    for source in status:
        source['lastAttemptAt'] = now
        source['lastSuccessAt'] = now if source['status'] == 'ok' else old_sources.get(source['name'], {}).get('lastSuccessAt')
    output = dict(schemaVersion=2, coverageVersion=10, lastAttemptAt=now, updatedAt=now if successful else previous.get('updatedAt'), offers=unique_offers, courses=courses, sources=enrich_sources(status),
                  note='Empleadores, servicios públicos y portales complementarios para categorías móviles. No garantiza encaje, contratación, plazas ni inscripción.')
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(target)
    print(json.dumps(dict(offers=len(offers), courses=len(courses), failedSources=sum(s['status']=='error' for s in status))))
    return output


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run()
