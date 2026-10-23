import json, sys, pathlib
import pytest
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import harness

FIX = harness.FIX
def fx(name): return json.loads((FIX / name).read_text(encoding="utf-8"))

EXTRA = lambda: {
    "**/data/companies.json*": fx("companies_fixture.json"),
    "**/data/scanner-status.json*": fx("status_fixture.json"),
    "**/data/scanner-report.json*": fx("report_fixture.json"),
    "**/data/companies-registry.json*": fx("registry_fixture.json"),
}

@pytest.fixture(scope="session")
def base_url():
    srv, url = harness.start_server()
    yield url
    srv.shutdown()

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()

@pytest.fixture
def make_page(browser, base_url):
    """Fábrica de páginas aisladas (contexto nuevo = localStorage vacío). Cualquier error
    de JavaScript no capturado FALLA el test al terminar."""
    made = []
    def _make(viewport=None, jobs=None, extra=True, init=None, jobs_status=200):
        ctx = browser.new_context(viewport=viewport or {"width": 1280, "height": 900})
        page = ctx.new_page()
        page.js_errors = []
        page.on("pageerror", lambda e: page.js_errors.append(str(e)))
        page.on("console", lambda m: page.js_errors.append(m.text) if m.type == "error" and "Failed to load resource" not in m.text and "net::ERR" not in m.text else None)
        if init:
            page.add_init_script(init)
        harness.install_routes(page, jobs=jobs, extra_files=EXTRA() if extra else None)
        if jobs_status != 200:
            page.route("**/data/jobs.json*", lambda r: r.fulfill(status=jobs_status, body="boom"))
        page.base = base_url
        made.append((ctx, page))
        return page
    yield _make
    for ctx, page in made:
        errs = list(page.js_errors)
        ctx.close()
        assert not errs, f"Errores de JavaScript en la página: {errs}"

def goto(page):
    page.goto(page.base + "/index.html")
    page.wait_for_function("typeof window.openVfxJobsPublic==='function' && typeof window.openGate==='function'")
    page.wait_for_function("window.__fb !== undefined")

def open_public(page):
    goto(page)
    page.evaluate("openVfxJobsPublic()")
    page.wait_for_selector("#vfxJobsBody .jp-card, #vfxJobsBody .jp-empty, #vfxJobsBody .jp-error")
    return page.locator("#vfxJobsBody")

def login(page, email="admin@test", password="good-pass"):
    page.evaluate("openGate()")
    page.fill("#gateEmail", email)
    page.fill("#gateIn", password)
    page.click("#gateGo")

def open_admin_panel(page):
    login(page)
    page.wait_for_selector("#admin-overlay.on")
    page.evaluate("showSec('vfxjobsview')")
    page.wait_for_selector("#vfxJobsAdminView .jp-card")
    return page.locator("#vfxJobsAdminView")

def ids(box):
    return sorted(box.locator(".jp-card").evaluate_all("els=>els.map(e=>e.dataset.job)"))
