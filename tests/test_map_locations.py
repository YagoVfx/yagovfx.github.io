import json
from pathlib import Path
from scanner.map_locations import locate

DATA=Path(__file__).resolve().parents[1]/'data'


def test_regions_and_remote_flags_do_not_become_fake_city_coordinates():
    assert locate('Remote, Europe, Spain, Worldwide','https://example.com')==[]
    points=locate('Barcelona / Madrid / Madrid','https://example.com')
    assert [p['city'] for p in points]==['Barcelona','Madrid']
    assert all(p['evidence']=='https://example.com' for p in points)
    assert locate('London, Ontario or Remote','https://example.com')[0]['lon']==-81.25
    assert locate('London, United Kingdom','https://example.com')[0]['lon']==-.13
    assert [p['city'] for p in locate('Montreal, Quebec, Canada','https://example.com')]==['Montreal']


def test_map_locations_have_evidence_and_do_not_hide_unlocated_studios():
    data=json.loads((DATA/'company-locations.json').read_text(encoding='utf-8'))
    names={c['name'] for c in data['companies']}
    registry=json.loads((DATA/'companies-registry.json').read_text(encoding='utf-8'))
    assert {c['name'] for c in registry['companies'] if c['state']!='unsupported'}<=names
    for c in data['companies']:
        for p in c['locations']:
            assert -90<=p['lat']<=90 and -180<=p['lon']<=180
            assert p['evidence'].startswith('https://')
    assert next(c for c in data['companies'] if c['name']=='Hexworks')['sharedSource']=='CI Games'


def test_mobile_bundles_same_cartography_and_valid_offline_snapshot():
    name='world-map.json'
    assert json.loads((DATA/name).read_text(encoding='utf-8'))==json.loads((DATA.parent/'mobile/assets'/name).read_text(encoding='utf-8'))
    # Locations and configured sources can evolve on the web after an APK
    # release; the bundled copy is an offline fallback, not a synchronization lock.
    bundle=DATA.parent/'mobile/assets'
    assert isinstance(json.loads((bundle/'company-locations.json').read_text(encoding='utf-8'))['companies'],list)
    assert isinstance(json.loads((bundle/'companies.json').read_text(encoding='utf-8')),list)
