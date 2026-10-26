"""Use the official public XML export, independent of cached search fragments."""
import re
from datetime import datetime
from xml.etree import ElementTree as ET
import requests
from scanner.mobile_careers import fold

EXPORT = 'https://administracion.gob.es/content/sling/endpoints/pag/front-elastic/empleo-elastic/exportar'


def parse_export(content, now):
    root = ET.fromstring(content)
    if root.tag != 'convocatorias':
        raise ValueError('PAG XML root changed')
    raw = list(root)
    if len(raw) >= 10000:
        raise ValueError('PAG export reached its public limit; coverage incomplete')
    rows = []
    for node in raw:
        def text(key): return node.findtext(key, '').strip()
        title = ' · '.join(v for v in [text('titulo'), text('descripcion')] if v)
        if not re.search(r'informatic|electric|electronic|telecom|mantenimiento|sistemas.*tecnolog', fold(title)):
            continue
        if text('viagrupoid') != '2' or text('idniveltitulacion') not in ('3', '4', '5'):
            continue
        free = int(text('plazaslibres') or 0)
        if free <= 0: continue
        dates = []
        for period in node.findall('plazos'):
            try:
                end = datetime.strptime(period.findtext('fechafin', ''), '%d/%m/%Y').date().isoformat()
                start = datetime.strptime(period.findtext('fechainicio', ''), '%d/%m/%Y').date().isoformat()
                if start <= now[:10] <= end: dates.append(end)
            except ValueError: continue
        if not dates: continue
        organization = text('organo')
        scope = 'local' if text('administracionconvocanteid') == '3' else 'autonomous' if text('ambito') == 'AUTONÓMICO' else 'state' if text('administracionconvocanteid') == '1' else 'other'
        if re.search('universi', fold(organization)): scope = 'university'
        municipality = 'vigo' if re.search(r'(?:ayuntamiento|concello) de vigo\b', fold(organization)) else 'coruna' if re.search(r'(?:ayuntamiento|concello) (?:de|da) (?:a |la )?coruna(?:,? a)?\b', fold(organization)) else None
        region = text('comunidadautonoma')
        area = 'galicia' if fold(region) == 'galicia' else 'national' if text('ambito') == 'NACIONAL' else 'other'
        reference = text('referencia') or text('id')
        documents = [n.findtext('masinformacion', '') for n in node.findall('disposiciones')]
        official = next((u for u in documents if u.startswith('https://www.boe.es/')), None)
        url = official or text('direccioninternet') or 'https://administracion.gob.es/empleopublico/resultados-empleo?pag_referencia='+reference
        qualification = text('titulacion') or text('grupo')
        rows.append(dict(id='pag-'+reference, reference=reference, title=title, organization=organization,
            location=' · '.join(v for v in [text('ambito'), region, text('provincia')] if v),
            area=area, adminScope=scope, municipality=municipality, qualification=qualification,
            fit='dam' if re.search(r'\bdam\b|desarrollo de aplicaciones multiplataforma', fold(qualification)) else 'review',
            places=int(text('plazasconvocadas') or 0), freePlaces=free, closingDate=max(dates),
            deadlineEvidence='Plazo publicado en la exportación oficial PAG; confirma bases y ampliaciones.',
            status='open', source='PAG · exportación XML oficial', url=url,
            access='Acceso libre; verificar requisitos específicos en las bases', checkedAt=now))
    return rows, len(raw)


def scan_export(now):
    # Same POST and limits used by the official Export XML button.
    response = requests.post(EXPORT, data=dict(type='xml', pag_viaGrupo='2', pag_tipoPlazo='1',
        exportSize='10000', pag_tam='10000', tam='10000', p='0', pag_desde='0',
        numRegistrosMostrar='10000', **{'p.limit':'10000'}), timeout=45)
    response.raise_for_status()
    rows, total = parse_export(response.content, now)
    return rows, [dict(name='PAG · exportación XML completa', status='ok', examined=total, matched=len(rows))]
