"""Refresh approximate city points from public employer listings (never geocode remote regions)."""
import json
import re
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from .adapters.greenhouse import extract_greenhouse_board
from .adapters.workable import extract_workable_account
from .adapters.smartrecruiters import extract_smartrecruiters_company

ROOT = Path(__file__).resolve().parents[1]
# City centres, approximate coordinates. Matching a city in an employer's
# structured location field is evidence of a location, not its headquarters.
CITIES = {
 'Barcelona':(41.39,2.17),'Madrid':(40.42,-3.70),'Alcobendas':(40.54,-3.64),'Valencia':(39.47,-0.38),'Seville':(37.39,-5.98),
 'London':(51.51,-0.13),'Cambridge':(52.21,0.12),'Leeds':(53.80,-1.55),'Edinburgh':(55.95,-3.19),
 'Guildford':(51.24,-0.57),'Nottingham':(52.95,-1.15),'Oxford':(51.75,-1.26),'Newcastle':(54.98,-1.61),
 'Leamington':(52.29,-1.54),'Brighton':(50.82,-0.14),'Dundee':(56.46,-2.97),'Horsham':(51.06,-0.33),
 'Los Angeles':(34.05,-118.24),'Santa Monica':(34.02,-118.49),'Culver City':(34.02,-118.40),
 'Burbank':(34.18,-118.31),'San Diego':(32.72,-117.16),'Carlsbad':(33.16,-117.35),'Irvine':(33.68,-117.83),
 'Seattle':(47.61,-122.33),'Bellevue':(47.61,-122.20),'Redmond':(47.67,-122.12),'San Francisco':(37.77,-122.42),
 'San Mateo':(37.56,-122.33),'Novato':(38.11,-122.57),'Austin':(30.27,-97.74),'Dallas':(32.78,-96.80),
 'New York':(40.71,-74.01),'Manhattan':(40.78,-73.97),'Boston':(42.36,-71.06),'Raleigh':(35.78,-78.64),
 'Cary':(35.79,-78.78),'Durham':(35.99,-78.90),'Troy':(42.73,-73.69),'Bend':(44.06,-121.32),
 'Montreal':(45.50,-73.57),'Montréal':(45.50,-73.57),'Toronto':(43.65,-79.38),'Vancouver':(49.28,-123.12),
 'Quebec City':(46.81,-71.21),'Oakville':(43.47,-79.69),'Ottawa':(45.42,-75.70),'Winnipeg':(49.90,-97.14),
 'Stockholm':(59.33,18.07),'Uppsala':(59.86,17.64),'Malmo':(55.61,13.00),'Malmö':(55.61,13.00),
 'Copenhagen':(55.68,12.57),'Oslo':(59.91,10.75),'Helsinki':(60.17,24.94),'Espoo':(60.21,24.66),
 'Warsaw':(52.23,21.01),'Warszawa':(52.23,21.01),'Krakow':(50.06,19.94),'Wroclaw':(51.11,17.04),
 'Berlin':(52.52,13.41),'Hamburg':(53.55,9.99),'Frankfurt':(50.11,8.68),'Munich':(48.14,11.58),
 'Darmstadt':(49.87,8.65),'Rotterdam':(51.92,4.48),'Amsterdam':(52.37,4.90),'Ghent':(51.05,3.72),
 'Paris':(48.86,2.35),'Lyon':(45.76,4.84),'Bordeaux':(44.84,-0.58),'Prague':(50.08,14.44),
 'Brno':(49.20,16.61),'Bratislava':(48.15,17.11),'Bucharest':(44.43,26.10),'Lisbon':(38.72,-9.14),
 'Porto':(41.16,-8.63),'Kyiv':(50.45,30.52),'Kiev':(50.45,30.52),'Limassol':(34.68,33.04),
 'Istanbul':(41.01,28.98),'Dubai':(25.20,55.27),'Tel Aviv':(32.09,34.78),'Singapore':(1.35,103.82),
 'Tokyo':(35.68,139.69),'Osaka':(34.69,135.50),'Seoul':(37.57,126.98),'Shanghai':(31.23,121.47),'Shenzhen':(22.54,114.06),
 'Bengaluru':(12.97,77.59),'Bangalore':(12.97,77.59),'Pune':(18.52,73.86),'Mumbai':(19.08,72.88),
 'Ho Chi Minh':(10.82,106.63),'Hanoi':(21.03,105.83),'Kuala Lumpur':(3.14,101.69),'Manila':(14.60,120.98),
 'Sydney':(-33.87,151.21),'Melbourne':(-37.81,144.96),'Wellington':(-41.29,174.78),
 'Sao Paulo':(-23.55,-46.63),'São Paulo':(-23.55,-46.63),'Recife':(-8.05,-34.88),'Buenos Aires':(-34.60,-58.38),
 'Mexico City':(19.43,-99.13),'Guadalajara':(20.67,-103.35),'Monterrey':(25.69,-100.32),
}


def locate(text, evidence):
    out, seen = [], set()
    london_ontario=bool(re.search(r'London\s*[,(/-]?\s*(?:Ontario|ON\b)',text,re.I))
    if london_ontario:
        out.append(dict(city='London (Ontario)',lat=42.98,lon=-81.25,evidence=evidence))
    for city,(lat,lon) in CITIES.items():
        if city=='London' and london_ontario:
            continue
        if (lat,lon) not in seen and re.search(r'(?<!\w)'+re.escape(city)+r'(?!\w)',text,re.I):
            out.append(dict(city=city,lat=lat,lon=lon,evidence=evidence)); seen.add((lat,lon))
    return out


def collect(c):
    url=c['careersUrl']; kind=c['type']; values=[]; evidence=url; direct=[]
    try:
        if kind=='greenhouse':
            evidence=f'https://boards-api.greenhouse.io/v1/boards/{extract_greenhouse_board(url)}/jobs'
            r=requests.get(evidence,timeout=20);r.raise_for_status()
            values=[j.get('location',{}).get('name','') for j in r.json()['jobs']]
        elif kind=='lever' or 'lever.co/' in url:
            slug=url.rstrip('/').split('/')[-1]; region='api.eu' if 'eu.lever' in url else 'api'
            evidence=f'https://{region}.lever.co/v0/postings/{slug}?mode=json'
            r=requests.get(evidence,timeout=20);r.raise_for_status()
            values=[j.get('categories',{}).get('location','') for j in r.json()]
        elif kind=='smartrecruiters':
            evidence=f'https://api.smartrecruiters.com/v1/companies/{extract_smartrecruiters_company(url)}/postings?limit=100'
            r=requests.get(evidence,timeout=20);r.raise_for_status()
            values=[j.get('location',{}).get('city','') for j in r.json()['content']]
        elif kind=='teamtailor':
            r=requests.get(url,timeout=20);r.raise_for_status()
            soup=BeautifulSoup(r.content,'html.parser')
            values=[a.get_text(' ',strip=True) for a in soup.select('a[href*="/locations/"]')]
            for tag in soup.select('[data-blocks--jobs-headquarter-value]'):
                location=json.loads(tag['data-blocks--jobs-headquarter-value'])
                values.append(location.get('city',''))
            for tag in soup.find_all(True):
                for key,value in tag.attrs.items():
                    if key.endswith('jobs-locations-value') or key.endswith('jobs-headquarter-value'):
                        locations=json.loads(value)
                        if isinstance(locations,dict): locations=[locations]
                        for location in locations:
                            lat,lon=location.get('lat'),location.get('long')
                            if lat is not None and lon is not None:
                                lat,lon=float(lat),float(lon)
                                if -90<=lat<=90 and -180<=lon<=180 and (lat,lon)!=(0,0):
                                    city=location.get('city') or next((name for name,(y,x) in CITIES.items() if abs(y-lat)<.4 and abs(x-lon)<.4),'Ubicación publicada')
                                    direct.append(dict(city=city,lat=round(lat,2),lon=round(lon,2),evidence=url))
        elif kind=='workable':
            slug=extract_workable_account(url); evidence=f'https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true'
            r=requests.get(evidence,timeout=20);r.raise_for_status()
            values=[str(j.get('city',''))+', '+str(j.get('country','')) for j in r.json()['jobs']]
        elif kind=='epic':
            evidence='https://greenhouse-service.debc.live.use1a.on.epicgames.com/api/job?limit=100&skip=0'
            r=requests.get(evidence,timeout=20);r.raise_for_status()
            values=[j.get('location',{}).get('name','') for j in r.json()['hits']]
        elif kind=='personio':
            host=urlsplit(url).netloc
            evidence=f'https://{host}/xml?language=en'
            r=requests.get(evidence,timeout=20);r.raise_for_status()
            values=[n.get_text(' ',strip=True) for n in BeautifulSoup(r.content,'xml').select('office')]
    except (requests.RequestException,ValueError,KeyError,TypeError):
        pass
    except AttributeError:
        pass
    points=[]
    for value in values:
        for point in locate(str(value or ''),evidence):
            if not any((p['lat'],p['lon'])==(point['lat'],point['lon']) for p in points):points.append(point)
    for point in direct:
        if not any(abs(p['lat']-point['lat'])<.5 and abs(p['lon']-point['lon'])<.5 for p in points):points.append(point)
    return dict(name=c['name'],locations=points)


def main():
    companies=json.loads((ROOT/'data/companies.json').read_text(encoding='utf-8'))
    with ThreadPoolExecutor(max_workers=6) as pool: rows=list(pool.map(collect,companies))
    jobs=json.loads((ROOT/'data/jobs.json').read_text(encoding='utf-8'))['jobs']
    for row in rows:
        for job in jobs:
            if job['company']==row['name'] and job.get('status')=='active':
                known={(p['lat'],p['lon']) for p in row['locations']}
                row['locations'] += [p for p in locate(job.get('location',''),job['url']) if (p['lat'],p['lon']) not in known]
    # Current official contact pages also cover studios with no open roles.
    official={
      'CI Games':('Warsaw Barcelona Bucharest London New York','https://cigames.com/en/contact/'),
      'Room8':('London Recife Montreal Limassol Warsaw','https://room8group.com/contact-us/'),
      'MercurySteam':('Madrid','https://www.mercurysteam.com/'),
      'Socialpoint':('Barcelona','https://www.socialpoint.es/join-us/'),
      'Saber Interactive Spain':('Alcobendas','https://saber-interactive-spain.jobs.personio.com/privacy-policy'),
      'Rovio':('Barcelona','https://www.rovio.com/game-studios/rovio-barcelona/'),
      'Capcom':('Osaka','https://www.capcom.co.jp/recruit/english/'),
      'SNK':('Osaka','https://www.snk-corp.co.jp/us/recruit/dev-recruit/'),
      'Piccolo Studio':('Barcelona','https://piccolo-studio.com/'),
      'Crema':('Madrid','https://crema.gg/careers/'),
      'Abylight':('Barcelona','https://abylight.com/'),
    }
    for row in rows:
        if row['name'] in official:
            text,url=official[row['name']];row['locations']=locate(text,url)
    rows.append(dict(name='Hexworks',sharedSource='CI Games',locations=locate('Barcelona Bucharest','https://cigames.com/en/contact/')))
    registry=json.loads((ROOT/'data/companies-registry.json').read_text(encoding='utf-8'))['companies']
    names={r['name'] for r in rows}
    for c in registry:
        if c['name'] not in names and c['state']!='unsupported':
            reference=official.get(c['name'])
            rows.append(dict(name=c['name'],locations=locate(*reference) if reference else []))
    output=dict(schemaVersion=1,note='Centros urbanos aproximados de ubicaciones publicadas; no son domicilios exactos ni garantizan empleo remoto. Las empresas sin evidencia se muestran sin localizar.',companies=rows)
    (ROOT/'data/company-locations.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{sum(bool(r["locations"]) for r in rows)}/{len(rows)} companies located')


if __name__=='__main__':main()
