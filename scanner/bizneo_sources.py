"""Discover public Bizneo job cards using separate title/location/workplace fields."""
import re
import hashlib
from datetime import date
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from scanner.mobile_sources import get, base_offer
from scanner.mobile_careers import classify_offer, fold, role_category


def read_board(host, company, key, now):
    out={};seen=set()
    for page in range(1,21):
        url=host+'/jobs'+('?page='+str(page) if page>1 else '')
        soup=BeautifulSoup(get(url).content,'html.parser')
        cards=soup.select('a.job-card[href]')
        if not cards:raise ValueError(company+': public job cards missing')
        signature=tuple(sorted(a['href'] for a in cards))
        if signature in seen:raise ValueError(company+': pagination repeated')
        seen.add(signature)
        for a in cards:
            heading=a.select_one('.title')
            if not heading:raise ValueError(company+': title missing')
            title=heading.get_text(' ',strip=True)
            if role_category(title)!='programming' or re.search(r'talent pool|crea tu propio|no esta tu oferta',fold(title)):continue
            parts=[s.get_text(' ',strip=True) for s in a.select('.details span:not(.aggregation)')]
            locations=[p for p in parts if not re.search(r'hibrid|presencial|remoto|teletrabajo',fold(p))]
            place=', '.join(locations)
            flags=[classify_offer(title,'',p) for p in locations]
            local=next((f for f in flags if f['inVigo'] or f['inCoruna']),None)
            remote=any(re.search(r'teletrabajo/remoto|100.?%.{0,12}remoto',fold(p)) for p in parts)
            if not local and not remote:continue
            link=urljoin(host,a['href']);detail=BeautifulSoup(get(link).content,'html.parser')
            main=detail.select_one('main') or detail
            description=main.get_text(' ',strip=True)
            row=base_offer(key,hashlib.sha256(link.encode()).hexdigest()[:20],title,company,place,description,link,now,company+' · Bizneo','employer')
            if local:row.update(inVigo=local['inVigo'],inCoruna=local['inCoruna'])
            row['workplace']='remote' if remote else 'hybrid' if any('hibrid' in fold(p) for p in parts) else 'onsite'
            row['postedDate']=None
            # Only explicit machine dates count as publication dates. "Publicada
            # 6 de Octubre" has no confirmed year and is not today's publication.
            published=detail.select_one('time[datetime],meta[property="article:published_time"]')
            if published:
                value=(published.get('datetime') or published.get('content') or '')[:10]
                try:date.fromisoformat(value);row['postedDate']=value
                except ValueError:pass
            out[row['id']]=row
        next_link=soup.find('a',href=True,string=re.compile(r'Siguiente|Next',re.I))
        if not next_link:break
    else:raise ValueError(company+': pagination incomplete')
    return list(out.values())


def infortec(now):
    return read_board('https://empleo.infortec.net','Infortec Consultores','infortec',now)
