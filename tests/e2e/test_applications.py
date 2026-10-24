import json
from urllib.parse import urlparse,unquote,parse_qs
from conftest import open_public

BASE='https://firestore.googleapis.com/v1/projects/portfolio-44b20/databases/(default)/documents/users/ylQ3m3XoCHTd0cwP7UQet7cSRpt1/applications'

def backend(page,records):
    def handle(route):
        assert route.request.headers.get('authorization')=='Bearer fixture-id-token'
        request=route.request
        if request.method=='DELETE':
            key=unquote(urlparse(request.url).path.rsplit('/',1)[-1])
            records.pop(key,None)
            route.fulfill(json={})
        elif request.method=='PATCH':
            key=unquote(urlparse(request.url).path.rsplit('/',1)[-1]);fields=request.post_data_json['fields']
            if parse_qs(urlparse(request.url).query).get('updateMask.fieldPaths'):
                records[key]['fields'].update(fields)
            else:records[key]={'fields':fields}
            route.fulfill(json=records[key])
        else:route.fulfill(json={'documents':list(records.values())})
    page.route(BASE+'**',handle)

def sign_in(box):
    box.get_by_role('tab',name='Mis candidaturas').click()
    form=box.locator('[data-app-login]')
    form.locator('[name=email]').fill('admin@test')
    form.locator('[name=password]').fill('good-pass')
    form.get_by_role('button',name='Iniciar sesión').click()
    box.locator('[data-app-logout]').wait_for()

def test_candidacy_syncs_between_two_devices_and_logout_clears_private_data(make_page):
    records={}
    first=make_page();second=make_page();backend(first,records);backend(second,records)
    web=open_public(first);mobile=open_public(second)
    sign_in(web);sign_in(mobile)
    web.get_by_role('tab',name='Ofertas',exact=True).click()
    web.locator('[data-job="gh-1"] [data-action="apply"]').click()
    web.locator('[data-job="gh-1"] [data-action="application-details"]').wait_for()
    assert 'gh-1' in records
    second.evaluate('VfxApplications.refresh()')
    mobile.locator('[data-app-status="gh-1"]').wait_for()
    mobile.locator('[data-app-status="gh-1"]').select_option('interview')
    second.wait_for_function("VfxApplications.get('gh-1').status==='interview'")
    first.evaluate('VfxApplications.refresh()')
    web.locator('[data-job="gh-1"] [data-action="application-details"]').filter(has_text='Entrevista').wait_for()
    second.once('dialog',lambda dialog:dialog.accept())
    mobile.locator('[data-app-delete="gh-1"]').click()
    second.wait_for_function("!VfxApplications.get('gh-1')")
    assert 'gh-1' not in records
    first.evaluate('VfxApplications.refresh()')
    web.locator('[data-job="gh-1"] [data-action="apply"]').wait_for()
    mobile.locator('[data-app-logout]').click()
    mobile.locator('[data-app-login]').wait_for()
    assert second.evaluate('VfxApplications.get("gh-1")') is None
    assert 'gh-1' not in second.evaluate('JSON.stringify(localStorage)')

def test_manual_previous_application_and_private_notes(make_page):
    records={};page=make_page();backend(page,records);box=open_public(page);sign_in(box)
    pane=box.locator('[data-pane=apps]');pane.get_by_text('Añadir una candidatura que ya enviaste',exact=True).click()
    form=pane.locator('[data-app-manual]');form.locator('[name=company]').fill('Previous Studio');form.locator('[name=title]').fill('VFX Artist');form.locator('[name=date]').fill('2026-09-01');form.get_by_role('button').click()
    pane.get_by_role('heading',name='VFX Artist',exact=True).wait_for()
    record=next(iter(records.values()))['fields'];assert record['company']['stringValue']=='Previous Studio'
    assert record['appliedAt']['stringValue'].startswith('2026-09-01')
    pane.get_by_text('Notas privadas',exact=True).click();notes=pane.locator('[data-app-notes]');notes.locator('textarea').fill('Follow up Friday');notes.get_by_role('button').click()
    page.wait_for_function("id=>VfxApplications.get(id).notes==='Follow up Friday'",arg=next(iter(records)))
    assert next(iter(records.values()))['fields']['notes']['stringValue']=='Follow up Friday'

def test_failed_write_does_not_mark_candidacy_as_saved(make_page):
    records={};page=make_page();backend(page,records);box=open_public(page);sign_in(box)
    page.route(BASE+'/*',lambda r:r.fulfill(status=403,json={'error':{'message':'PERMISSION_DENIED'}}))
    box.get_by_role('tab',name='Ofertas',exact=True).click();box.locator('[data-job="gh-1"] [data-action="apply"]').click()
    box.locator('[data-pane=apps] [role=alert]').wait_for()
    assert page.evaluate('VfxApplications.get("gh-1")') is None
    assert 'reglas privadas' in box.locator('[data-pane=apps]').inner_text()


def test_private_applications_forms_are_accessible_on_mobile(make_page):
    from test_mobile_a11y import AXE,run_axe
    import pytest
    if AXE is None:pytest.skip('axe-core no instalado')
    records={};page=make_page(viewport={'width':390,'height':900});backend(page,records);box=open_public(page)
    box.get_by_role('tab',name='Mis candidaturas').click()
    assert run_axe(page,'#vfxJobsBody [data-pane=apps]')==[]
    sign_in(box)
    assert run_axe(page,'#vfxJobsBody [data-pane=apps]')==[]
