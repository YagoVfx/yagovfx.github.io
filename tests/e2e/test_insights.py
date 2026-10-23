import json
import pytest
from conftest import open_public


@pytest.mark.parametrize('width',[390,1280])
def test_map_platform_statistics_and_company_selection(make_page,width):
    page=make_page(viewport={'width':width,'height':900})
    locations={'companies':[
      {'name':'Room8','locations':[{'city':'London','lat':51.5,'lon':-.1,'evidence':'https://room8group.com/contact-us/'}]},
      {'name':'Hexworks','sharedSource':'CI Games','locations':[{'city':'Barcelona','lat':41.39,'lon':2.17,'evidence':'https://cigames.com/en/contact/'}]},
      {'name':'Unlocated','locations':[]},
    ]}
    page.route('**/data/company-locations.json',lambda r:r.fulfill(body=json.dumps(locations),content_type='application/json'))
    box=open_public(page)
    box.get_by_role('tab',name='Mapa y estadísticas').click()
    radar=box.locator('[data-pane="insights"]')
    radar.get_by_role('heading',name='Mapa de empresas').wait_for()
    assert radar.locator('.ji-ranking li').count()>0
    radar.locator('[data-map-company]').select_option(label='Hexworks')
    assert radar.locator('[data-map-canvas] text').all_text_contents()==['Hexworks']
    assert 'portal compartido con CI Games' in radar.locator('[data-map-detail]').inner_text()
    radar.get_by_role('button',name='Ampliar mapa').click()
    assert '150%' in radar.locator('[data-map-canvas] svg').get_attribute('style')
    radar.locator('[data-map-names]').uncheck()
    assert radar.locator('[data-map-canvas] text').count()==0
    assert 'Unlocated' in radar.inner_text() or 'Unlocated' in radar.inner_html()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
