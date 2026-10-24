"""Stratos' advertised public RSS and public employment list (not collaborations)."""
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, parse_qs
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

from scanner.mobile_careers import HEADERS, fold
from scanner.mobile_sources import base_offer, clean
from scanner.radar_sources import vfx_role

RSS='https://stratos-ad.com/rss?source=jobs'
LIST='https://stratos-ad.com/trabajo'


def public_response(url):
    response=requests.get(url,headers=HEADERS,timeout=30)
    response.raise_for_status()
    return response


def job_id(url):
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in ['stratos-ad.com','www.stratos-ad.com'] or parsed.path!='/trabajo':return None
    value=(parse_qs(parsed.query).get('job') or [''])[0]
    return value if value.isdigit() else None


def read(now):
    feed=public_response(RSS)
    try:root=ET.fromstring(feed.content)
    except ET.ParseError as e:raise ValueError('Stratos no entrega un RSS público reconocible; no se importan anuncios') from e
    channel=root.find('channel')
    if channel is None or (channel.findtext('title') or '').strip() not in ['Stratos','Stratos :: Trabajo']:raise ValueError('Identidad del RSS de Stratos no reconocida')
    response=public_response(LIST)
    soup=BeautifulSoup(response.content,'html.parser')
    if not any(fold(h.get_text(' ',strip=True))=='trabajo' for h in soup.select('h1,h2')):
        raise ValueError('Listado público de trabajo Stratos no reconocido')
    listing={}
    for tr in soup.select('tr'):
        cells=tr.find_all('td',recursive=False)
        if len(cells)!=4:continue
        a=cells[1].select_one('a[href]')
        if not a:continue
        identifier=job_id('https://stratos-ad.com'+a['href']) if a['href'].startswith('/') else job_id(a['href'])
        if identifier:listing[identifier]=dict(title=a.get_text(' ',strip=True),location=cells[2].get_text(' ',strip=True),company=cells[3].get_text(' ',strip=True))
    if not listing:raise ValueError('Stratos no entrega filas de empleo reconocibles; no se considera una búsqueda vacía')
    rows=[]
    for item in channel.findall('item'):
        # The RSS also contains news and collaboration requests. Only employment.
        if fold(item.findtext('category') or '')!='trabajo':continue
        url=item.findtext('link') or '';identifier=job_id(url)
        if identifier not in listing:continue
        metadata=listing[identifier]
        if not vfx_role(metadata['title']):continue
        published=parsedate_to_datetime(item.findtext('pubDate'))
        if published.tzinfo is None:published=published.replace(tzinfo=timezone.utc)
        age=(datetime.fromisoformat(now.replace('Z','+00:00'))-published).days
        if age<0 or age>120:continue
        body=clean(item.findtext('description'))
        # Don't accidentally classify the studio's historical description as job requirements.
        description=body.split('Texto de la oferta:',1)[-1].strip()
        row=base_offer('stratos',identifier,metadata['title'],metadata['company'],metadata['location'],description,
                       url,now,'Stratos · Trabajo','job-board')
        row.update(category='vfx',postedDate=published.date().isoformat())
        if 'hibrido' in fold(metadata['location']):row['workplace']='hybrid'
        elif 'remoto' in fold(metadata['location']):row['workplace']='remote'
        elif 'presencial' in fold(metadata['location']):row['workplace']='onsite'
        if 'autonomo/freelance' in fold(body):row['requirements'].append('Anunciado como autónomo/freelance; no es contrato laboral')
        if re.search(r'pago aplazado|revenue.?share|porcentaje de ventas|% de ventas',fold(body)):
            row['requirements'].append('Revisar remuneración: menciona pago aplazado o participación en ventas')
        rows.append(row)
    return rows
