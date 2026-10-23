"""Regresión: las funcionalidades que ya existían siguen funcionando tras la V2."""
import re
from conftest import goto, login, open_public

ADMIN_SECTIONS = ["reel", "companies", "videos", "tools", "profile", "cv", "layout", "themes", "anim", "skin",
                  "posts", "vfxjobs", "vfxjobsview", "links", "import", "seo", "settings"]


def test_homepage_renders_and_has_no_js_errors(make_page):
    page = make_page(); goto(page)
    page.wait_for_timeout(500)
    assert page.title()
    assert page.locator("header.topbar").is_visible()
    assert len(page.inner_text("body")) > 200            # contenido real, no página en blanco


def test_visitor_language_switch_still_works_and_persists_locally(make_page):
    page = make_page(); goto(page)
    before = page.inner_text("body")
    page.evaluate("setLang('es')")
    after = page.inner_text("body")
    assert after != before                                # el texto de la web cambia de idioma
    assert '"lang":"es"' in page.evaluate("localStorage.getItem('vfx-v6')")


def test_public_jobs_button_appears_when_enabled_and_opens_the_panel_like_a_user(make_page):
    page = make_page(); goto(page)
    assert not page.is_visible("#vfxJobsNavBtn")           # oculto por defecto
    login(page); page.wait_for_selector("#admin-overlay.on")
    page.evaluate("setVfxJobsPublicVisible(true)")
    page.evaluate("document.getElementById('admin-overlay').classList.remove('on')")
    assert page.is_visible("#vfxJobsNavBtn")
    page.click("#vfxJobsNavBtn")                           # clic real, no llamada directa
    page.wait_for_selector("#vfxJobsBody .jp-card")
    assert page.locator("#vfxJobsBody .jp-card").count() == 6
    page.click("#vfxJobsOverlay .vjo-back")
    assert not page.evaluate("document.getElementById('vfxJobsOverlay').classList.contains('open')")


def test_every_admin_section_opens_without_errors(make_page):
    page = make_page(); goto(page)
    login(page); page.wait_for_selector("#admin-overlay.on")
    for sec in ADMIN_SECTIONS:
        page.evaluate(f"showSec('{sec}')")
        assert page.evaluate(f"document.getElementById('sec-{sec}').classList.contains('active')"), sec
    page.evaluate("showSec('vfxjobsview')")
    page.wait_for_selector("#vfxJobsAdminView .jp-card")


def test_vfx_company_manager_section_still_renders_and_lists_companies(make_page):
    page = make_page(); goto(page)
    login(page); page.wait_for_selector("#admin-overlay.on")
    page.evaluate("showSec('vfxjobs')")
    assert page.is_visible("#sec-vfxjobs")
    assert page.locator("#sec-vfxjobs").inner_text().strip() != ""
    assert page.locator("#sec-vfxjobs button, #sec-vfxjobs input").count() > 3       # controles del gestor intactos


def test_scanner_diagnostics_modal_still_works_and_escapes_hostile_content(make_page):
    hostile = [
        {"company": "Evil <img src=x onerror=window.__xss=3> Co", "status": "error", "error": "boom <script>window.__xss=4</script>", "ats": "custom"},
        {"company": "Fine Co", "status": "ok", "jobsFound": 2, "totalPostingsSeen": 10},
        {"company": "Off Co", "status": "disabled"},
        {"source": "Adzuna", "company": "(Adzuna)", "status": "partial", "jobsFound": 1},
    ]
    page = make_page(extra=False)
    page.route("**/data/scanner-status.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=__import__("json").dumps(hostile)))
    goto(page)
    login(page); page.wait_for_selector("#admin-overlay.on")
    page.evaluate("openVfxDiagnostics()")
    page.wait_for_selector("#mBody .vfx-diag-row")
    body = page.inner_text("#mBody")
    assert "Evil <img src=x onerror=window.__xss=3> Co" in body and "<script>" in body        # literal, no ejecutado
    assert page.evaluate("window.__xss") is None
    assert page.locator("#mBody img, #mBody script").count() == 0
    low = body.lower()   # el CSS pone las etiquetas en mayúsculas
    assert "fine co" in low and "10 posting(s) seen" in low and "disabled" in low and "partial" in low


def test_scanner_diagnostics_handles_missing_status_file(make_page):
    page = make_page(extra=False)
    page.route("**/data/scanner-status.json*", lambda r: r.fulfill(status=404, body="no"))
    goto(page); login(page); page.wait_for_selector("#admin-overlay.on")
    page.evaluate("openVfxDiagnostics()")
    page.wait_for_function("document.getElementById('mBody').innerText.includes('No se pudo leer')")


def test_legacy_jobs_json_format_renders_with_notice(make_page):
    """Compatibilidad hacia atrás: un data/jobs.json del scanner antiguo (sin campos V2) se sigue mostrando."""
    legacy = {"lastUpdated": "2026-10-20T00:00:00Z", "jobs": [
        {"id": "gh-1", "company": "Old Co", "title": "Senior VFX Artist", "url": "https://x.test/1", "location": "Madrid",
         "workplaceType": "unknown", "remoteScope": "Unknown", "ats": "greenhouse", "matchType": "exactMatch",
         "firstSeen": "2026-10-19T00:00:00Z", "lastSeen": "2026-10-20T00:00:00Z", "status": "active"}]}
    page = make_page(jobs=legacy)
    box = open_public(page)
    assert box.locator(".jp-card").count() == 1
    assert "formato anterior" in box.locator("[data-ref=banner]").inner_text()


def test_old_index_backup_page_is_not_loaded_by_the_new_site(make_page, base_url):
    html = __import__("urllib.request").request.urlopen(base_url + "/index.html").read().decode()
    assert "index_.html" not in html
    assert re.search(r'href="assets/jobs/jobs\.css"', html) and "assets/jobs/jobs-core.js" in html and "assets/jobs/jobs-ui.js" in html
