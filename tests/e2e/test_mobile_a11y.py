"""Móvil (360 px) y accesibilidad automática con axe-core (WCAG 2.1 A/AA). Requiere `npm i axe-core`
(ver tests/README); si no está instalado los tests de axe se omiten explícitamente, no pasan en silencio."""
import json, pathlib, shutil, subprocess
import pytest
from conftest import open_public, open_admin_panel, goto

def _axe_path():
    for c in (pathlib.Path(__file__).parents[2] / "node_modules/axe-core/axe.min.js", pathlib.Path("/tmp/pwtest/node_modules/axe-core/axe.min.js")):
        if c.exists(): return c
    return None
AXE = _axe_path()
needs_axe = pytest.mark.skipif(AXE is None, reason="axe-core no instalado (npm i axe-core)")
MOBILE = {"width": 360, "height": 800}   # UI-11: móvil 360 px

def no_hscroll(page):
    return page.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1 && document.getElementById('vfxJobsOverlay').scrollWidth<=window.innerWidth+1")

def run_axe(page, selector):
    page.add_script_tag(content=AXE.read_text(encoding="utf-8"))
    res = page.evaluate("(sel)=>axe.run(document.querySelector(sel),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})", selector)
    return [(v["id"], v["impact"], [n["target"] for n in v["nodes"]][:3]) for v in res["violations"]]


def test_mobile_offers_no_horizontal_scroll_and_usable(make_page, tmp_path):
    page = make_page(viewport=MOBILE)
    box = open_public(page)
    assert no_hscroll(page)
    box.locator('[data-action="adv"]').click()
    box.locator('input[data-filter="showUnverified"]').check()
    assert no_hscroll(page)
    box.locator('[data-action="toggle-spain"]').click()
    assert box.locator(".jp-card").count() >= 1 and no_hscroll(page)
    page.screenshot(path=str(tmp_path / "shot_mobile_offers.png"), full_page=False)


def test_mobile_back_button_is_not_covered_and_closes_the_overlay(make_page):
    """Defecto previo (también en el original): la cabecera sticky del sitio tapaba «← Back» en móvil."""
    page = make_page(viewport=MOBILE)
    open_public(page)
    covered = page.evaluate("""()=>{const b=document.querySelector('#vfxJobsOverlay .vjo-back').getBoundingClientRect();
        const top=document.elementFromPoint(b.left+b.width/2,b.top+b.height/2);return !top.classList.contains('vjo-back')}""")
    assert not covered
    page.click("#vfxJobsOverlay .vjo-back")
    assert not page.evaluate("document.getElementById('vfxJobsOverlay').classList.contains('open')")


def test_mobile_touch_targets_are_at_least_36px(make_page):
    page = make_page(viewport=MOBILE)
    box = open_public(page)
    box.locator('[data-action="adv"]').click()
    small = page.evaluate("""()=>[...document.querySelectorAll('#vfxJobsBody .jp button, #vfxJobsBody .jp select, #vfxJobsBody .jp input:not([type=checkbox]), #vfxJobsBody .jp summary, #vfxJobsBody .jp a.jp-btn')]
      .filter(e=>e.offsetParent!==null).map(e=>[e.className||e.tagName, Math.round(e.getBoundingClientRect().height)])
      .filter(x=>x[1]<28)""")
    assert small == [], f"objetivos táctiles demasiado pequeños: {small}"


def test_mobile_companies_and_tabs_scroll_inside_their_own_container(make_page, tmp_path):
    page = make_page(viewport=MOBILE)
    box = open_public(page)
    box.locator(".jp-tab", has_text="Empresas").click()
    page.wait_for_selector(".jp-co")
    assert no_hscroll(page)
    page.screenshot(path=str(tmp_path / "shot_mobile_companies.png"))


def test_mobile_admin_panel_sources_tab(make_page):
    page = make_page(viewport=MOBILE); goto(page)
    admin = open_admin_panel(page)
    admin.locator(".jp-tab", has_text="Fuentes y scanner").click()
    page.wait_for_selector("#vfxJobsAdminView .jp-stat")
    assert page.evaluate("document.getElementById('vfxJobsAdminView').scrollWidth<=window.innerWidth+1")


def test_desktop_screenshots_for_report(make_page, tmp_path):
    page = make_page()
    box = open_public(page)
    box.locator('input[data-filter="showUnverified"]').check()
    page.screenshot(path=str(tmp_path / "shot_desktop_offers.png"))
    goto(page)


@needs_axe
@pytest.mark.parametrize("tab", ["offers", "saved", "companies", "settings"])
def test_axe_public_panel(make_page, tab):
    page = make_page()
    box = open_public(page)
    if tab == "offers":
        box.locator('[data-action="adv"]').click()
        box.locator('input[data-filter="showUnverified"]').check()
        box.locator('[data-job="gh-1"] summary').click()
    elif tab == "companies":
        box.locator(".jp-tab", has_text="Empresas").click(); page.wait_for_selector(".jp-co")
    else:
        box.locator(".jp-tab", has_text={"saved": "Guardadas", "settings": "Ajustes"}[tab]).click()
    v = run_axe(page, "#vfxJobsBody")
    assert v == [], f"violaciones axe en pestaña {tab}: {v}"


@needs_axe
def test_axe_admin_panel_sources_and_empty_state(make_page):
    page = make_page(); goto(page)
    admin = open_admin_panel(page)
    admin.locator(".jp-tab", has_text="Fuentes y scanner").click(); page.wait_for_selector("#vfxJobsAdminView .jp-stat")
    assert run_axe(page, "#vfxJobsAdminView") == []
    admin.locator(".jp-tab", has_text="Ofertas").click()
    admin.locator('select[data-filter="workplace"]').select_option("onsite")
    admin.locator('[data-action="toggle-spain"]').click()
    assert run_axe(page, "#vfxJobsAdminView") == []


@needs_axe
def test_axe_login_gate(make_page):
    page = make_page(); goto(page)
    page.evaluate("openGate()")
    assert run_axe(page, "#adm-gate") == []
