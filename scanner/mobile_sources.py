"""Complementary sources, explicitly distinguished from direct employer ATS."""
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

from scanner.mobile_careers import HEADERS, classify_offer, fold, role_category


def get(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response


def clean(value):
    return BeautifulSoup(html.unescape(value or '').replace('\\n', ' '), 'html.parser').get_text(' ', strip=True)


def permitted_remote(region, description):
    """Remote is not itself evidence that Spain is eligible. Reject explicit restrictions."""
    region = fold(region)
    if not re.search(r'world|anywhere|global|europe|emea|spain|espana|\beu\b', region):
        return False
    body = fold(description)
    if re.search(r'\bremote\s*(?:[-:(]\s*|from\s+(?:the\s+)?|(?=u\.s\.))(?:us\b|u\.s\.|united states|hong kong)', body):
        return False
    if re.search(r'(?:telework|remote|work from home|teletrabajo).{0,30}(?:one|1|two|2) days? (?:per|a) week', body):
        return False
    # Structured region metadata is sometimes broader than the actual role.
    restrictions = re.findall(r'(?:must (?:be |currently )?(?:based|reside|live)|only (?:hiring|available)|location\s*:|remote-first\s*\().{0,100}', body)
    foreign = r'argentina|united states|\busa\b|\bu\.s\.|canada|brazil|india|philippines|united kingdom|\buk only\b|australia'
    for line in restrictions:
        if re.search(foreign, line) and not re.search(r'spain|espana|europe|world|anywhere|global', line):
            return False
    return not bool(re.search(r'(?:us|usa|uk|canada|india|australia)[ -]only|must.{0,25}(?:us citizen|us resident)', body))


def base_offer(key, identifier, title, company, location, description, url, now, source, kind):
    meta = classify_offer(title, description, location)
    if re.search(r'\bmid\b|[3-9]\+?\s*(?:years|anos).{0,20}experien', fold(title + ' ' + description)):
        meta['experience'] = 'experienced'
    return dict(id=f'career-{key}-{identifier}', category='programming', title=title,
                company=company, location=location, description=description[:4500], url=url,
                source=source, sourceKind=kind, checkedAt=now, closingDate=None, **meta)


def wwr(now):
    root = ET.fromstring(get('https://weworkremotely.com/categories/remote-programming-jobs.rss').content)
    items = root.findall('./channel/item')
    if not items: raise ValueError('WWR RSS has no recognized items')
    out = []
    for item in items:
        full = item.findtext('title') or ''
        company, _, title = full.partition(': ')
        if not title: continue
        # Category alone sometimes includes business roles; require software title.
        if not role_category(title) == 'programming' and not re.search(r'engineer|devops', fold(title)): continue
        description = clean(item.findtext('description'))
        region = item.findtext('region') or ''
        if not permitted_remote(region, description): continue
        url = item.findtext('link') or ''
        if not url.startswith('https://weworkremotely.com/remote-jobs/'): continue
        published = parsedate_to_datetime(item.findtext('pubDate')).astimezone(timezone.utc)
        if (datetime.fromisoformat(now.replace('Z', '+00:00')) - published).days > 60: continue
        row = base_offer('wwr', hashlib.sha256(url.encode()).hexdigest()[:20], title, company, region,
                         description, url, now, 'We Work Remotely', 'job-board')
        row.update(workplace='remote', postedDate=published.date().isoformat(),
                   requirements=row['requirements'] + ['Confirmar país de contratación, idioma y horario en la fuente'])
        out.append(row)
    return out


def remoteok(now):
    data = get('https://remoteok.com/api').json()
    if not isinstance(data, list) or not data or 'legal' not in data[0]: raise ValueError('Remote OK API schema changed')
    out = []
    for job in data[1:]:
        title = job.get('position') or ''
        if role_category(title) != 'programming' and not re.search(r'software engineer|devops', fold(title)): continue
        description = clean(job.get('description'))
        region = job.get('location') or ''
        if not permitted_remote(region, description): continue
        published = datetime.fromisoformat(job['date'].replace('Z', '+00:00'))
        if (datetime.fromisoformat(now.replace('Z', '+00:00')) - published).days > 60: continue
        url = job.get('url') or ''
        parsed_url = urlparse(url)
        if parsed_url.scheme != 'https' or parsed_url.hostname != 'remoteok.com': continue
        row = base_offer('remoteok', str(job['id']), title, job.get('company') or 'Empresa no indicada',
                         region, description, url, now, 'Remote OK', 'job-board')
        row.update(workplace='remote', postedDate=published.date().isoformat())
        row['requirements'].append('Confirmar país de contratación, idioma y horario en Remote OK')
        out.append(row)
    return out


def employer_html(host, company, key, now):
    soup = BeautifulSoup(get(host + '/jobs').content, 'html.parser')
    links = {urljoin(host, a['href']): a.get_text(' ', strip=True) for a in soup.select('a[href]') if '/jobs/' in a['href']}
    if not links: raise ValueError(company + ': job list not recognized')
    out = []
    for url, label in links.items():
        if role_category(label) != 'programming' and not re.search(r'\bsap\b|soporte tecnico', fold(label)): continue
        if 'talent pool' in fold(label): continue  # spontaneous applications are not open vacancies
        # Locations are in each card, not inferred from the company's offices.
        meta = classify_offer(label, label, label)
        if not (meta['inVigo'] or meta['inCoruna']): continue
        detail = BeautifulSoup(get(url).content, 'html.parser')
        heading = detail.select_one('h1')
        if heading is None: raise ValueError(company + ': detail not recognized')
        title = heading.get_text(' ', strip=True)
        description = detail.get_text(' ', strip=True)
        for marker in ['Descripción', 'Descripcion']:
            if marker in description:
                description = description.split(marker, 1)[1]; break
        row = base_offer(key, hashlib.sha256(url.encode()).hexdigest()[:20], title, company,
                         'Vigo' if meta['inVigo'] else 'A Coruña', description, url, now,
                         company + ' · Portal de empresa', 'employer')
        row['workplace'] = 'hybrid' if 'hibrido' in fold(label) else 'remote' if 'remoto' in fold(label) else 'onsite'
        row['postedDate'] = None  # never replace an unknown publication date with today's scan date
        out.append(row)
    return out


# Public, verified original listing URLs. Each scan revalidates JobPosting and closing date.
# These seed URLs supplement discovery; they are not claimed to cover all Adecco vacancies.
ADECCO_SEEDS = [
    'https://www.adecco.com/es-es/ofertas-trabajo/tcnico-a-de-instalaciones-elctricas-vigo-pontevedra/282105f449ae2cf5b10490d81d5dd3da',
    'https://www.adecco.com/es-es/ofertas-trabajo/tcnico-a-electricista-vigo-pontevedra/80ffc59f1975dc2fc3244768626cb7cd',
    'https://www.adecco.com/es-es/ofertas-trabajo/tcnicoa-de-mantenimiento-industrial-vigo-pontevedra/79cb6c6381cbb930df342015ee3a0a67',
]


def adecco(now):
    out = []
    for url in ADECCO_SEEDS:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code in (404,410): continue  # confirmed removed listing
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        raw = soup.select_one('script[type="application/ld+json"]')
        if not raw: raise ValueError('Adecco: JobPosting not recognized')
        job = json.loads(raw.string)
        if job.get('@type') != 'JobPosting': raise ValueError('Adecco schema changed')
        end = (job.get('validThrough') or '').strip()[:10]
        if end and end < now[:10]: continue
        title = job['title']; description = clean(job.get('description'))
        location = job['jobLocation']['address']['addressLocality']
        meta = classify_offer(title, description, location)
        if not (meta['inVigo'] or meta['inCoruna']): continue
        if role_category(title) != 'electricity': continue
        out.append(dict(id='career-adecco-' + job['jobId'].lower(), category='electricity',
                        title=title, company='Adecco · empresa cliente no indicada', location=location,
                        url=url, source='Adecco', sourceKind='recruitment-agency', description=description[:4500],
                        checkedAt=now, closingDate=end or None, postedDate=job.get('datePosted', '')[:10], **meta))
    return out


def additional_sources():
    from scanner.radar_sources import sources
    from scanner.local_employers import sources as local_sources
    return [
        ('wwr', 'We Work Remotely · RSS público', wwr),
        ('remoteok', 'Remote OK · API pública', remoteok),
        ('imatia', 'Imatia · Portal de empresa', lambda now: employer_html('https://jobs.imatia.com', 'Imatia', 'imatia', now)),
        ('inprosec', 'Inprosec · Portal de empresa', lambda now: employer_html('https://talent.inprosec.com', 'Inprosec', 'inprosec', now)),
        ('adecco', 'Adecco · fichas originales seleccionadas', adecco),
    ] + sources() + local_sources()
