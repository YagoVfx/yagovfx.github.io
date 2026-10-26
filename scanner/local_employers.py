"""Public discovery for software and local electrical maintenance roles."""
import re
from urllib.parse import urljoin, urlencode
from bs4 import BeautifulSoup
from scanner.mobile_sources import get, clean, base_offer
from scanner.mobile_careers import classify_offer, fold, role_category


def electrical_description(text):
    return bool(re.search(r'electric|electromecanic|alumbrado|cablead|cuadros electric|automatismos', fold(text)))


def sopra(now):
    out = []
    endpoint = 'https://api.smartrecruiters.com/v1/companies/SopraSteria1/postings'
    for offset in range(0, 600, 100):
        data = get(endpoint+'?'+urlencode(dict(country='es',limit=100,offset=offset))).json()
        if not isinstance(data.get('content'),list): raise ValueError('Sopra API layout changed')
        for job in data['content']:
            title=job['name'];loc=job['location'];city=loc.get('city','')
            if loc.get('country','').lower()!='es' or role_category(title)!='programming':continue
            meta=classify_offer(title,'',city)
            if not (meta['inVigo'] or meta['inCoruna'] or loc.get('remote') or re.search(r'remoto|remote|teletrabajo',fold(title))):continue
            detail=get(job['ref']).json()
            if detail.get('active') is False:continue
            description=' '.join(clean(s.get('text')) for s in detail['jobAd']['sections'].values() if isinstance(s,dict))
            row=base_offer('sopra',job['id'],title,'Sopra Steria',city+', España',description,
                detail.get('applyUrl') or 'https://jobs.smartrecruiters.com/SopraSteria1/'+job['id'],now,'Sopra Steria · SmartRecruiters','employer')
            if loc.get('remote') and row['workplace']!='hybrid':row['workplace']='remote'
            if not(row['inVigo'] or row['inCoruna'] or row['workplace']=='remote'):continue
            row['postedDate']=job.get('releasedDate','')[:10]
            out.append(row)
        if offset+len(data['content'])>=data.get('totalFound',0):break
    else:raise ValueError('Sopra pagination incomplete')
    return out


def cofrico(now):
    host='https://cofrico.viterbit.site/'
    soup=BeautifulSoup(get(host).content,'html.parser')
    cards=soup.select('a.vb-job-title[href]')
    if not cards:raise ValueError('Cofrico job list changed')
    out=[]
    for a in cards:
        marker=a.parent.select_one('.la-map-marker')
        city=marker.parent.get_text(' ',strip=True) if marker else ''
        meta=classify_offer(a.get_text(' ',strip=True),'',city)
        if not(meta['inVigo'] or meta['inCoruna']):continue
        title=a.get_text(' ',strip=True)
        if not re.search(r'frigor|refriger|electric|mantenim|climatiz',fold(title)):continue
        url=urljoin(host,a['href']);detail=BeautifulSoup(get(url).content,'html.parser')
        description=detail.get_text(' ',strip=True)
        if not electrical_description(description):continue
        row=base_offer('cofrico',a['href'].strip('/'),title,'Cofrico',city,description,url,now,'Cofrico · Viterbit','employer')
        row.update(category='electricity',workplace='onsite',postedDate=None)
        row['requirements'].append('Revisar acreditaciones de refrigeración, gases fluorados y especialidad requerida')
        out.append(row)
    return out


def randstad(now):
    from scanner.radar_sources import jobposting,identifier
    host='https://www.randstad.es';links=set()
    for city_path in ['p-pontevedra/c-vigo','p-coruna/c-coruna-a']:
        seen=set()
        for page in range(1,9):
            url=host+'/candidatos/ofertas-empleo/'+city_path+('/' if page==1 else '/pg-'+str(page)+'/')
            soup=BeautifulSoup(get(url).content,'html.parser')
            all_links={urljoin(host,a['href']):a.get_text(' ',strip=True) for a in soup.select('a[href]') if '/ofertas-empleo/oferta/' in a['href']}
            if not all_links:
                if page==1:raise ValueError('Randstad local result list not recognized')
                break
            signature=tuple(sorted(all_links))
            if signature in seen:raise ValueError('Randstad pagination repeated')
            seen.add(signature)
            links.update(u for u,t in all_links.items() if role_category(t)=='electricity')
            if not soup.select('a[href*="/pg-'+str(page+1)+'/"]'):break
        else:raise ValueError('Randstad pagination incomplete')
    out=[]
    for url in sorted(links):
        soup=BeautifulSoup(get(url).content,'html.parser');job=jobposting(soup)
        if not job:raise ValueError('Randstad JobPosting missing')
        location=job.get('jobLocation') or {};location=location[0] if isinstance(location,list) else location
        city=(location.get('address') or {}).get('addressLocality','')
        description=clean(job.get('description'));title=job['title']
        meta=classify_offer(title,description,city)
        if not(meta['inVigo'] or meta['inCoruna']) or not electrical_description(description):continue
        end=(job.get('validThrough') or '')[:10]
        if end and end<now[:10]:continue
        row=base_offer('randstad',identifier(url),title,'Randstad · empresa cliente',city,description,url,now,'Randstad · portal original','recruitment-agency')
        row.update(category='electricity',workplace='onsite',postedDate=(job.get('datePosted') or '')[:10],closingDate=end or None,contractType=job.get('employmentType'))
        out.append(row)
    return out


def sources():
    return [('sopra','Sopra Steria · SmartRecruiters',sopra),('cofrico','Cofrico · Viterbit',cofrico),('randstad','Randstad · electricidad local',randstad)]
