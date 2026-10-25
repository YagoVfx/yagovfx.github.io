"""Group public adverts by original vacancy URL, retaining every source ID."""
import hashlib
from urllib.parse import urlsplit, parse_qsl, urlencode


def vacancy_url(value):
    p = urlsplit(value or '')
    if not p.netloc:
        return ''
    query = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith('utm_') and k.lower() not in ('source', 'ref')]
    return p.netloc.lower() + p.path.rstrip('/') + '?' + urlencode(sorted(query))


def specific_url(value):
    key = vacancy_url(value)
    _, _, query = key.partition('?')
    last = urlsplit(value or '').path.rstrip('/').split('/')[-1].lower()
    return key if query or last not in ('', 'careers', 'jobs', 'job', 'vacancies', 'open-positions', 'join-us') else ''


def unify(offers, direct):
    official = {specific_url(r.get('url')): r for r in direct if r.get('status') == 'active' and r.get('directUrl') is not False and not r.get('urlIsLanding')}
    official.pop('', None)
    groups = {}
    for row in offers:
        if row.get('category') != 'vfx':
            groups[row['id']] = dict(row)
            continue
        key = specific_url(row.get('originalUrl') or row.get('url')) if not row.get('urlIsLanding') else ''
        match = official.get(key)
        identity = match['id'] if match else 'career-vfx-' + hashlib.sha256(key.encode()).hexdigest()[:20] if key else row['id']
        aliases = list(dict.fromkeys([row['id'], *row.get('sourceIds', [])]))
        if match:
            aliases += [match['id']]
        if identity not in groups:
            groups[identity] = dict(row, id=identity, sourceIds=[], foundIn=[])
        group = groups[identity]
        if not row.get('retainedAfterFailure'):
            group.pop('retainedAfterFailure', None)
            if row.get('checkedAt'):
                group['checkedAt'] = max(group.get('checkedAt', ''), row['checkedAt'])
        group['sourceIds'] = list(dict.fromkeys(group['sourceIds'] + aliases))
        group['foundIn'] = list(dict.fromkeys(group['foundIn'] + row.get('foundIn', [row['source']])))
        if match:
            group['url'] = match['url']
            match['sourceIds'] = list(dict.fromkeys(match.get('sourceIds', []) + group['sourceIds']))
            match['foundIn'] = list(dict.fromkeys([match.get('ats', 'Empresa'), *group['foundIn']]))
    return list(groups.values())
