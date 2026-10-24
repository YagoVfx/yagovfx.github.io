from conftest import open_public


def test_eu_filter_persists_without_duplicate_location_options(make_page):
    page=make_page();box=open_public(page)
    box.locator('[data-action="toggle-eu"]').click()
    assert box.locator('[data-action="toggle-eu"]').get_attribute('aria-pressed')=='true'
    assert box.locator('[data-action="toggle-spain"]').get_attribute('aria-pressed')=='false'
    assert box.locator('select[data-filter=location]').input_value()=='eu'
    page.reload();box=open_public(page)
    assert box.locator('select[data-filter=location]').input_value()=='eu'
    assert box.locator('select[data-filter=location] option[value=eu]').count()==1
    assert 'Unión Europea' in box.locator('select[data-filter=location] option[value=eu]').inner_text()
    box.locator('[data-action="toggle-spain"]').click()
    assert box.locator('[data-action="toggle-eu"]').get_attribute('aria-pressed')=='false'
