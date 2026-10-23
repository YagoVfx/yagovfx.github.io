import json
import pytest
from conftest import open_public


def radar_page(make_page,width=1280,locations=None):
    page=make_page(viewport={'width':width,'height':900})
    locations=locations or {'companies':[
      {'name':'Room8','locations':[{'city':'London','lat':51.5,'lon':-.1,'evidence':'https://room8group.com/contact-us/'}]},
      {'name':'Hexworks','sharedSource':'CI Games','locations':[{'city':'Barcelona','lat':41.39,'lon':2.17,'evidence':'https://cigames.com/en/contact/'}]},
      {'name':'Unlocated','locations':[]},
    ]}
    page.route('**/data/company-locations.json',lambda r:r.fulfill(body=json.dumps(locations),content_type='application/json'))
    box=open_public(page)
    assert box.get_by_role('link',name='Jobs VFX Scanner en GitHub').get_attribute('href').endswith('/vfx-jobs-scanner.yml')
    box.get_by_role('tab',name='Mapa y estadísticas').click()
    radar=box.locator('[data-pane="insights"]')
    radar.locator('[data-map-cluster]').first.wait_for()
    return page,radar


@pytest.mark.parametrize('width',[390,1280])
def test_green_marker_keeps_camera_until_all_offices_requested(make_page,width):
    locations={'companies':[{'name':'Room8','locations':[
        {'city':'London','lat':51.5,'lon':-.1,'evidence':'https://room8group.com/contact-us/'},
        {'city':'Tokyo','lat':35.68,'lon':139.69,'evidence':'https://room8group.com/contact-us/'},
    ]}]}
    page,radar=radar_page(make_page,width,locations)
    camera=radar.locator('[data-map-svg]>g').first.get_attribute('transform')
    radar.locator('[data-map-cluster]').first.click()
    assert radar.locator('[data-map-svg]>g').first.get_attribute('transform')==camera
    detail=radar.locator('[data-map-detail]')
    assert 'London' in detail.inner_text() and 'Tokyo' not in detail.inner_text()
    assert radar.locator('[data-map-company]').input_value()==''
    detail.get_by_role('button',name='Ver todas sus sedes').click()
    assert radar.locator('[data-map-svg]>g').first.get_attribute('transform')!=camera
    assert radar.locator('[data-map-company]').input_value()=='Room8'
    assert 'London' in detail.inner_text() and 'Tokyo' in detail.inner_text()


@pytest.mark.parametrize('width',[390,1280])
def test_clusters_company_selection_search_and_reset(make_page,width):
    page,radar=radar_page(make_page,width)
    assert radar.locator('.ji-ranking li').count()>0
    assert radar.locator('[data-map-cluster]').count()==1
    assert radar.locator('[data-map-svg] text').all_text_contents()==['2']
    radar.locator('[data-map-cluster]').click()
    assert radar.locator('.ji-company-pick').count()==2
    radar.locator('[data-pick-company="Hexworks"]').click()
    assert radar.locator('[data-map-detail] h4').inner_text()=='Hexworks'
    assert 'portal compartido con ci games' in radar.locator('[data-map-detail]').inner_text().lower()
    assert radar.locator('[data-map-company]').input_value()=='Hexworks'
    assert radar.locator('[data-map-svg] text').all_text_contents()==['Barcelona']
    radar.get_by_role('button',name='Ver todo el mundo').click()
    radar.locator('[data-map-search]').fill('london')
    assert radar.locator('.ji-company-pick strong').all_text_contents()==['Room8']
    radar.locator('[data-map-search]').fill('no matching studio')
    assert radar.locator('[data-map-cluster]').count()==0
    assert 'No hay empresas' in radar.locator('[data-map-detail]').inner_text()
    radar.get_by_role('button',name='Ver todo el mundo').click()
    assert 'Unlocated' in radar.inner_html()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')


def test_mouse_wheel_drag_and_keyboard_explore_the_map(make_page):
    page,radar=radar_page(make_page)
    surface=radar.locator('.ji-map-surface')
    surface.hover()
    before=radar.locator('[data-map-scale]').inner_text()
    page.mouse.wheel(0,-550)
    page.wait_for_timeout(100)
    assert radar.locator('[data-map-scale]').inner_text()!=before
    before_transform=radar.locator('[data-map-svg]>g').first.get_attribute('transform')
    bounds=surface.bounding_box()
    page.mouse.move(bounds['x']+bounds['width']*.4,bounds['y']+bounds['height']*.5)
    page.mouse.down()
    page.mouse.move(bounds['x']+bounds['width']*.4+80,bounds['y']+bounds['height']*.5+30,steps=8)
    page.mouse.up()
    assert radar.locator('[data-map-svg]>g').first.get_attribute('transform')!=before_transform
    surface.focus()
    before=radar.locator('[data-map-scale]').inner_text()
    surface.press('+')
    assert radar.locator('[data-map-scale]').inner_text()!=before


def test_two_finger_pinch_on_mobile_web(make_page):
    page,radar=radar_page(make_page,390)
    surface=radar.locator('.ji-map-surface')
    surface.scroll_into_view_if_needed()
    bounds=surface.bounding_box();x=bounds['x']+bounds['width']/2;y=bounds['y']+bounds['height']/2
    session=page.context.new_cdp_session(page)
    before=radar.locator('[data-map-scale]').inner_text()
    def touches(distance):return [{'x':x-distance,'y':y,'id':1},{'x':x+distance,'y':y,'id':2}]
    session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':touches(25)})
    session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':touches(70)})
    session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    assert radar.locator('[data-map-scale]').inner_text()!=before


def test_map_controls_are_accessible(make_page):
    from test_mobile_a11y import AXE,run_axe
    if AXE is None:
        pytest.skip('axe-core no instalado')
    page,radar=radar_page(make_page,390)
    assert run_axe(page,'#vfxJobsBody [data-pane="insights"]')==[]
