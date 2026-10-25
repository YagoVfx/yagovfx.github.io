"""Selected paid original courses, with transparent original currency and pricing."""
import re
from datetime import date
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from scanner.mobile_sources import get
from scanner.mobile_careers import fold


def coloso(now):
    exchange_url='https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml'
    rate, rate_date = None, None
    try:
        xml=ET.fromstring(get(exchange_url).content)
        for cube in xml.iter():
            if 'time' in cube.attrib:rate_date=cube.attrib['time']
            if cube.attrib.get('currency')=='USD':rate=float(cube.attrib['rate'])
        age=(date.fromisoformat(now[:10])-date.fromisoformat(rate_date)).days
        if not 0<=age<=10:rate=None
    except Exception:
        rate=None
    courses=[
        ('vfxartist-kisonglee-us','Bringing Artistic Game Effects to Life with Niagara','intermediate',26+2/60,'Mejorar diseño, timing y efectos para videojuegos con Niagara. Audio coreano; revisar subtítulos y requisitos de Unreal.'),
        ('vfxartist-kisonglee2-us','Unlocking the Magic','advanced',21+56/60,'Efectos de fantasía y habilidades con Niagara. Requiere base previa; comprobar idiomas y programa completo.'),
        ('vfxartist-heyyo-us','Mastering the Mechanics of Advanced Niagara','advanced',30+12/60,'Técnicas avanzadas de Niagara y materiales. Audio japonés y subtítulos según ficha; comprobar idioma antes de comprar.'),
    ]
    out=[]
    for slug, expected, level, hours, description in courses:
        url='https://coloso.global/en/products/'+slug
        soup=BeautifulSoup(get(url).content,'html.parser')
        text=soup.get_text(' ',strip=True)
        if fold(expected) not in fold(text):raise ValueError('Coloso course title changed: '+slug)
        price=re.search(r'Price\s*USD\s*([\d,]+\.\d{2})',text)
        if not price:raise ValueError('Coloso public price not recognized: '+slug)
        usd=float(price.group(1).replace(',',''))
        title=next((h.get_text(' ',strip=True) for h in soup.select('h1,h2,h3') if fold(expected) in fold(h.get_text(' ',strip=True))),expected)
        out.append(dict(id='course-coloso-'+slug,kind='course',title=title,provider='Coloso',source='Coloso',topic='vfx',
            url=url,sourceUrl=url,price=round(usd/rate,2) if rate else None,sourcePrice=usd,sourceCurrency='USD',
            priceIsEstimate=True,exchangeRateDate=rate_date,exchangeRateSourceUrl=exchange_url,
            durationHours=round(hours,2),modality='online',level=level,learningGoal='improve',
            language='Audio japonés; subtítulos en inglés; español no confirmado' if 'heyyo' in slug else 'Audio coreano; subtítulos en inglés y español automático según la ficha',
            description=description,availability='Autoaprendizaje de pago. Precio publicado sujeto a descuentos, impuestos y condiciones de compra.',
            checkedAt=now))
    return out


def animum(now):
    url='https://www.animum3d.com/vfx-efectos-visuales/'
    soup=BeautifulSoup(get(url).content,'html.parser')
    link=next((a for a in soup.select('a[href]') if 'master' in fold(a.get_text(' ',strip=True)) and 'composicion' in fold(a.get_text(' ',strip=True))),None)
    if not link:raise ValueError('Animum specific master course link not found')
    from urllib.parse import urljoin
    detail_url=urljoin(url,link['href'])
    detail=BeautifulSoup(get(detail_url).content,'html.parser')
    if not re.search(r'vfx|efectos visuales',fold(detail.get_text(' ',strip=True))):raise ValueError('Animum course content changed')
    return [dict(id='course-animum-vfx',kind='course',title='Máster VFX y Composición',provider='Animum',source='Animum',topic='vfx',
        url=detail_url,sourceUrl=url,price=None,modality='online',level='intermediate',learningGoal='new',
        description='Formación de larga duración en VFX y composición. Compara su enfoque de cine/composición con tu objetivo de VFX para videojuegos. No se presupone que entre en 800 €.',
        availability='Precio, admisión y próxima convocatoria por consultar con el centro. No es una inscripción ni una recomendación de compra.',checkedAt=now)]


def sources():
    return [('coloso','Coloso · formación de pago',coloso),('animum','Animum · formación de pago',animum)]
