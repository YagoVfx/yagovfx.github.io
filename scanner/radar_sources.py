"""Public employer boards and VFX job-board discovery. No applicant accounts."""
import hashlib
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlencode
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from scanner.mobile_sources import get, clean, base_offer
from scanner.mobile_careers import classify_offer, fold, role_category, HEADERS
import requests


def identifier(url):
    return hashlib.sha256(url.encode()).hexdigest()[:20]


def vfx_role(title):
    return bool(re.search(r'\bvfx\b|visual effects|technical.{0,3}artist|technical.{0,3}art\b|tech.{0,3}artist|tech.{0,3}art\b', fold(title)))


def programming_role(title):
    return role_category(title) == 'programming' or bool(re.search(r'\bsap\b|soporte informatico|software engineer|product engineer|tech lead|architect|devops|front.end|back.end', fold(title)))


def local_or_remote(meta):
    return meta['inVigo'] or meta['inCoruna'] or meta['workplace'] == 'remote'


def jobposting(soup):
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            text = script.string or script.get_text()
            try:
                data = json.loads(text, strict=False)
            except ValueError:
                # GamesJobsDirect publishes invalid semicolons after address strings.
                repaired = re.sub(r'("(?:[^"\\]|\\.)*")\s*;', r'\1,', text)
                repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
                data = json.loads(repaired, strict=False)
        except (ValueError, TypeError): continue
        candidates = data if isinstance(data, list) else data.get('@graph', [data])
        for item in candidates:
            if item.get('@type') == 'JobPosting': return item
    return None


def inditex(now):
    data = get('https://zara.recruitee.com/api/offers/').json()
    if not isinstance(data.get('offers'), list): raise ValueError('Inditex Recruitee layout changed')
    out = []
    for raw in data['offers']:
        title = raw.get('title') or ''
        # A talent pool and a graduate programme are not a specific open job.
        if not programming_role(title) or re.search(r'join us|boost|graduate|summer in tech', fold(title)): continue
        description = clean((raw.get('description') or '') + ' ' + (raw.get('requirements') or ''))
        location = raw.get('city') or ''
        if not location and raw.get('locations'): location = ', '.join(x.get('city', '') for x in raw['locations'])
        row = base_offer('inditex', str(raw['id']), title, 'Inditex / Zara', location, description,
                         raw['careers_url'], now, 'Inditex / Zara · Recruitee', 'employer')
        if raw.get('remote'): row['workplace'] = 'remote'
        elif raw.get('hybrid'): row['workplace'] = 'hybrid'
        else: row['workplace'] = 'onsite'
        if row['inCoruna'] and row['workplace'] != 'remote':
            # The broad Inditex city label may refer to Arteixo. It is not municipal evidence.
            row['inCoruna'] = False
        if not local_or_remote(row): continue
        row['postedDate'] = (raw.get('published_at') or raw.get('created_at') or '')[:10] or None
        row['requirements'].append('Confirmar sede real: A Coruña puede referirse al entorno de Arteixo')
        out.append(row)
    return out


def indra(now):
    host = 'https://careers.indragroup.com'
    links = {}
    # Public SuccessFactors search, including pagination. Location ES alone is not remote evidence.
    for query in ['Vigo', 'Coruña', 'remoto']:
        for offset in range(0, 100, 25):
            url = host + '/search/?' + urlencode({'q': query, 'startrow': offset, 'locale': 'es_ES'})
            soup = BeautifulSoup(get(url).content, 'html.parser')
            rows = soup.select('tr.data-row')
            if not soup.select_one('#searchresults') and 'No se han encontrado' not in soup.get_text():
                raise ValueError('Indra result layout changed')
            for tr in rows:
                a = tr.select_one('.jobTitle-link')
                if a and programming_role(a.get_text(' ', strip=True)):
                    links[urljoin(host, a['href'])] = tr.select_one('td.colLocation').get_text(' ', strip=True)
            if len(rows) < 25: break
        else: raise ValueError('Indra pagination incomplete')
    out = []
    for url, location in links.items():
        soup = BeautifulSoup(get(url).content, 'html.parser')
        data = jobposting(soup)
        heading = soup.select_one('h1')
        if not heading: raise ValueError('Indra detail layout changed')
        title = data['title'] if data else heading.get_text(' ', strip=True)
        content = soup.select_one('.jobdescription') or soup.select_one('.job')
        description = clean(data.get('description')) if data else content.get_text(' ', strip=True) if content else ''
        if not description: raise ValueError('Indra job description missing')
        row = base_offer('indra', identifier(url), title, 'Indra / Minsait', location, description, url,
                         now, 'Indra Group · Portal de empresa', 'employer')
        if not local_or_remote(row): continue
        # Some descriptions advertise optional remote days; these are not full remote outside Galicia.
        if not (row['inVigo'] or row['inCoruna']) and re.search(r'hibrid|[1-4] dias.{0,25}teletrabajo', fold(description)): continue
        row['postedDate'] = data.get('datePosted', '')[:10] if data else None
        row['closingDate'] = (data.get('validThrough') or '')[:10] or None if data else None
        if row['closingDate'] and row['closingDate'] < now[:10]: continue
        out.append(row)
    return out


def veolia(now):
    endpoint = 'https://api.smartrecruiters.com/v1/companies/VeoliaEnvironnementSA/postings'
    out = []
    for offset in range(0, 1200, 100):
        data = get(endpoint + '?' + urlencode(dict(country='es', limit=100, offset=offset))).json()
        if not isinstance(data.get('content'), list): raise ValueError('Veolia API changed')
        for raw in data['content']:
            location = raw['location']['city']
            # Some ads use a province capital in metadata but name another town in the title.
            if re.search(r'bergondo|arteixo|cambre|culleredo|redondela|porrino|\bmos\b', fold(raw['name'])): continue
            meta = classify_offer(raw['name'], '', location)
            if not (meta['inVigo'] or meta['inCoruna']) or role_category(raw['name']) != 'electricity': continue
            detail = get(raw['ref']).json()
            if detail.get('active') is False: continue
            description = ' '.join(clean(s.get('text')) for s in detail['jobAd']['sections'].values() if isinstance(s, dict))
            if not re.search(r'electric|electromecanic|alumbrado|cablead', fold(description)): continue
            row = base_offer('veolia', raw['id'], raw['name'], 'Veolia', location, description,
                             detail.get('applyUrl') or f'https://jobs.smartrecruiters.com/VeoliaEnvironnementSA/{raw["id"]}',
                             now, 'Veolia · SmartRecruiters', 'employer')
            row.update(category='electricity', postedDate=raw.get('releasedDate', '')[:10])
            row['url'] = f'https://jobs.smartrecruiters.com/VeoliaEnvironnementSA/{raw["id"]}'
            out.append(row)
        if offset + len(data['content']) >= data.get('totalFound', 0): return out
    raise ValueError('Veolia pagination incomplete')


def workwithindies(now):
    root = ET.fromstring(get('https://workwithindies.com/careers/rss.xml').content)
    items = root.findall('./channel/item')
    if not items: raise ValueError('Work With Indies RSS layout changed')
    out = []
    for item in items:
        label = item.findtext('title') or ''
        if not vfx_role(label): continue
        url = item.findtext('link') or ''
        if not url.startswith('https://www.workwithindies.com/careers/'): continue
        soup = BeautifulSoup(get(url).content, 'html.parser')
        closed = soup.select_one('.closed-notif')
        if closed and 'w-condition-invisible' not in closed.get('class', []): continue
        data = jobposting(soup)
        if not data: raise ValueError('Work With Indies JobPosting missing')
        title = clean(data['title'])
        if not vfx_role(title): continue
        company = data['hiringOrganization']['name']
        location = label.rsplit('to work from ', 1)[-1] if 'to work from ' in label else 'Por confirmar'
        row = base_offer('wwi', identifier(url), title, company, location, clean(data.get('description')),
                         url, now, 'Work With Indies', 'job-board')
        row.update(category='vfx', postedDate=(data.get('datePosted') or '')[:10] or None,
                   workplace='remote' if data.get('jobLocationType') == 'TELECOMMUTE' else 'unknown')
        row['requirements'].append('Comprobar países, contrato y vigencia en la ficha; portal complementario')
        out.append(row)
    return out


def hitmarker(now):
    # This scoped search-only key is published in the public page, refreshed each scan,
    # and used only for the same search operation. Never request administrative endpoints.
    page = get('https://hitmarker.net/jobs').text
    match = re.search(r'window\.TSSK\s*=\s*"([^"]+)"', page)
    if not match: raise ValueError('Hitmarker public search configuration changed')
    out = {}
    for term in ['VFX', 'Technical Artist']:
        for number in range(1, 6):
            response = requests.get('https://search.hitmarker.com/collections/hitmarker_jobs_open/documents/search',
                params=dict(q=term, query_by='title', per_page=100, page=number),
                headers={**HEADERS, 'X-TYPESENSE-API-KEY': match.group(1)}, timeout=30)
            response.raise_for_status(); data = response.json()
            if not isinstance(data.get('hits'), list): raise ValueError('Hitmarker results changed')
            for hit in data['hits']:
                raw = hit['document']; title = raw['title']
                if not vfx_role(title): continue
                location = ', '.join(dict.fromkeys(x['title'] for loc in raw.get('jobLocation', []) for x in [loc, *loc.get('parents', [])]))
                row = base_offer('hitmarker', raw['id'], title, raw['jobCompany']['title'], location or 'Por confirmar',
                    clean(raw.get('jobDescriptionHtml')), raw['url'], now, 'Hitmarker', 'job-board')
                row.update(category='vfx', workplace='remote' if raw.get('jobIsRemote') else 'onsite',
                           postedDate=datetime.fromtimestamp(raw['postDate'], timezone.utc).date().isoformat())
                if (datetime.fromisoformat(now.replace('Z','+00:00')) - datetime.fromtimestamp(raw['postDate'],timezone.utc)).days > 120: continue
                if (raw.get('jobLevel') or {}).get('id') in ['senior','lead','director']: row['experience']='experienced'
                original = raw.get('jobApplicationUrl') or ''
                if original.startswith('https://'): row['originalUrl'] = original
                row['requirements'].append('Revisar países permitidos y modalidad en el anuncio original')
                out[row['id']] = row
            if number * 100 >= data.get('found', 0): break
        else: raise ValueError('Hitmarker pagination incomplete')
    return list(out.values())


def gamesjobsdirect(now):
    host = 'https://www.gamesjobsdirect.com'
    links = set()
    for term in ['vfx', 'technical artist']:
        for page in range(1, 7):
            soup = BeautifulSoup(get(host + '/results?' + urlencode(dict(k=term, page=page))).content, 'html.parser')
            found = {urljoin(host,a['href']) for a in soup.select('a[href]') if re.match(r'/job/[^/]+/[^/]+/\d+',a['href']) and vfx_role(a.get_text(' ',strip=True))}
            old = len(links); links.update(found)
            if not found or len(links)==old: break
        else: raise ValueError('GamesJobsDirect pagination incomplete')
    out=[]
    for url in links:
        response=get(url);soup=BeautifulSoup(response.content,'html.parser');data=jobposting(soup)
        if not data:
            text=fold(soup.get_text(' ',strip=True))
            if re.search(r'job.{0,30}(expired|no longer|not available)|vacancy.{0,25}(closed|expired)',text):continue
            raise ValueError('GamesJobsDirect JobPosting missing: '+url)
        if not vfx_role(data.get('title','')):continue
        end=(data.get('validThrough') or '')[:10]
        if end and end < now[:10]:continue
        location=data.get('jobLocation') or {};location=location[0] if isinstance(location,list) and location else location
        address=location.get('address') or {}
        country=address.get('addressCountry','');country=country.get('name','') if isinstance(country,dict) else country
        place=', '.join(str(x) for x in [address.get('addressLocality'),country] if x)
        row=base_offer('ggd',identifier(url),clean(data['title']),data['hiringOrganization']['name'],place or 'Por confirmar',clean(data.get('description')),url,now,'GamesJobsDirect','job-board')
        row.update(category='vfx',postedDate=(data.get('datePosted') or '')[:10] or None,closingDate=end or None)
        out.append(row)
    return out


def artstation(now):
    # The public endpoint currently returns HTTP 403. Surface that failure explicitly;
    # do not silently claim a working integration or try to bypass the challenge.
    from scanner.source_errors import IntegrationPending
    raise IntegrationPending('ArtStation: integración pendiente de un formato público validado. No se cuenta como fuente operativa.')


def xunta_employment(now):
    from scanner.source_errors import IntegrationPending
    raise IntegrationPending('Xunta empleo privado: integración pendiente. SNE, DIPLOS y CNTG se consultan por separado.')


def probe_xunta_employment():
    """Manual diagnostic, separate from the scheduled source health check."""
    url='https://emprego.xunta.gal/es/demandantes/busca-empleo/busca-trabajo-en-galicia'
    with requests.Session() as session:
        response=session.get(url,headers=HEADERS,timeout=30);response.raise_for_status()
        soup=BeautifulSoup(response.content,'html.parser');form=soup.select_one('#buscador-emprego-form-id')
        if not form:raise ValueError('Xunta employment form changed')
        data={x['name']:x.get('value','') for x in form.select('input[name]')}
        data.update(selector_provincia='1',selector_orden='4',emprego='electric',op='Buscar emprego')
        response=session.post(url,data=data,headers=HEADERS,timeout=30)
        if response.status_code==400 and 'provided host name is not valid' in response.text:
            raise ValueError('El formulario oficial devuelve HTTP 400: host no válido. Cursos DIPLOS/CNTG y ofertas SNE se consultan por separado.')
        response.raise_for_status()
        raise ValueError('Respuesta Xunta recibida; resultados pendientes de validar. No se importan sin comprobar formato.')


def sources():
    from scanner.stratos_source import read as stratos
    return [('inditex','Inditex / Zara · Recruitee',inditex),('indra','Indra / Minsait · SuccessFactors',indra),
            ('veolia','Veolia · SmartRecruiters',veolia),('wwi','Work With Indies · RSS + ficha',workwithindies),
            ('hitmarker','Hitmarker · búsqueda pública',hitmarker),('ggd','GamesJobsDirect · fichas',gamesjobsdirect),
            ('stratos','Stratos · RSS + listado público',stratos),
            ('artstation','ArtStation · consulta automática',artstation),('xunta','Xunta · ofertas privadas',xunta_employment)]
