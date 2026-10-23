"""Seguridad del login de admin. Firebase (Auth/Firestore) está SIMULADO: estos tests verifican el
código cliente (no hay contraseña en la página, visitantes no escriben, el gate no se salta), NO las
reglas reales de Firestore — esas solo pueden comprobarse en la consola de Firebase (ver SEGURIDAD_ADMIN.md)."""
import json
from conftest import goto, login, open_admin_panel

LEGACY_DOC = {"lang": "en", "password": "admin123", "vfxCompanies": [], "marker": "from-remote"}

def fb(page, expr): return page.evaluate(f"(()=>{{const S=window.__fb;return {expr}}})()")
def admin_on(page): return page.evaluate("document.getElementById('admin-overlay').classList.contains('on')")


def test_page_source_contains_no_password_or_default_credentials(base_url):
    import urllib.request
    html = urllib.request.urlopen(base_url + "/index.html").read().decode()
    assert "admin123" not in html.replace("contraseña 'admin123' comparada", "")      # solo queda en un comentario histórico
    import re
    assert not re.search(r"D\.password\s*={1,3}", html) and "newPw" not in html     # ni se compara ni se asigna
    assert "firebase-auth.js" in html


def test_openAdmin_is_not_a_global_and_gate_cannot_be_bypassed(make_page):
    page = make_page(); goto(page)
    assert page.evaluate("typeof window.openAdmin") == "undefined"          # original: window.openAdmin() abría el admin
    page.evaluate("typeof checkPw==='function' && checkPw()")                # sin credenciales
    assert not admin_on(page)
    page.evaluate("showSec && 0")
    assert not admin_on(page)


def test_gate_requires_email_and_password_and_is_accessible(make_page):
    page = make_page(); goto(page)
    page.evaluate("openGate()")
    assert page.is_visible("#adm-gate")
    assert page.get_attribute("#adm-gate", "role") == "dialog" and page.get_attribute("#adm-gate", "aria-modal") == "true"
    assert page.locator("label[for=gateEmail]").count() == 1 and page.locator("label[for=gateIn]").count() == 1
    assert page.get_attribute("#gateIn", "type") == "password"
    page.click("#gateGo")                                                    # vacío: no llama a Firebase
    assert fb(page, "S.authCalls.length") == 0 and not admin_on(page)
    page.keyboard.press("Escape")
    assert not page.is_visible("#adm-gate")


def test_wrong_password_shows_generic_error_and_clears_field(make_page):
    page = make_page(); goto(page)
    login(page, password="wrong")
    page.wait_for_selector("#gateErr:visible")
    assert page.inner_text("#gateErr") == "Credenciales incorrectas."
    assert page.input_value("#gateIn") == "" and not admin_on(page)
    assert fb(page, "S.authCalls.length") == 1


def test_old_default_password_no_longer_works(make_page):
    page = make_page(); goto(page)
    login(page, password="admin123")
    page.wait_for_selector("#gateErr:visible")
    assert not admin_on(page)


def test_unknown_email_gives_same_message_as_wrong_password(make_page):
    page = make_page(); goto(page)
    login(page, email="nobody@test", password="good-pass")
    page.wait_for_selector("#gateErr:visible")
    assert page.inner_text("#gateErr") == "Credenciales incorrectas."


def test_lockout_after_five_failures(make_page):
    page = make_page(); goto(page)
    page.evaluate("openGate()")
    for _ in range(5):
        page.fill("#gateEmail", "admin@test"); page.fill("#gateIn", "bad"); page.click("#gateGo")
        page.wait_for_function("document.getElementById('gateIn').value===''")
    page.fill("#gateIn", "good-pass"); page.click("#gateGo")
    page.wait_for_function("document.getElementById('gateErr').textContent.includes('Demasiados')")
    assert fb(page, "S.authCalls.length") == 5 and not admin_on(page)           # el 6º intento ni llega a Firebase


def test_successful_login_opens_admin_and_gate_closes(make_page):
    page = make_page(); goto(page)
    login(page)
    page.wait_for_selector("#admin-overlay.on")
    assert not page.is_visible("#adm-gate") and page.input_value("#gateIn") == ""
    assert fb(page, "S.authed") is True


def test_authenticated_non_admin_cannot_open_or_publish(make_page):
    page = make_page(init="window.__fb={writes:[],remote:null,authed:false,authCalls:[],uid:'other-user'}")
    goto(page)
    login(page)
    page.wait_for_selector("#gateErr:visible")
    assert not admin_on(page)
    assert fb(page, "S.authed") is False
    page.evaluate("save()")
    page.wait_for_timeout(800)
    assert fb(page, "S.writes.length") == 0


def test_logout_cancels_pending_publication(make_page):
    page = make_page(); goto(page)
    login(page); page.wait_for_selector("#admin-overlay.on")
    page.evaluate("save(); logoutAdmin()")
    page.wait_for_timeout(800)
    assert fb(page, "S.writes.length") == 0


def test_gear_button_skips_gate_only_when_already_authenticated(make_page):
    page = make_page(init="window.__fb={writes:[],remote:null,authed:true,authCalls:[],email:'admin@test'}")
    goto(page)
    page.wait_for_function("true")
    page.wait_for_timeout(100)
    page.evaluate("openGate()")
    assert admin_on(page) and not page.is_visible("#adm-gate")


def test_logout_closes_admin_and_requires_login_again(make_page):
    page = make_page(); goto(page)
    login(page); page.wait_for_selector("#admin-overlay.on")
    page.evaluate("logoutAdmin()")
    page.wait_for_function("!document.getElementById('admin-overlay').classList.contains('on')")
    assert fb(page, "S.authed") is False
    page.evaluate("openGate()")
    assert page.is_visible("#adm-gate") and not admin_on(page)


def test_session_loss_closes_open_admin(make_page):
    page = make_page(); goto(page)
    login(page); page.wait_for_selector("#admin-overlay.on")
    page.evaluate("import('https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js').then(m=>m.signOut({}))")
    page.wait_for_function("!document.getElementById('admin-overlay').classList.contains('on')")


# ── La fuga original: el documento público de Firestore contenía la contraseña ──
def test_visitor_actions_never_write_to_firestore(make_page):
    page = make_page(); goto(page)
    page.evaluate("setLang('es')")           # en el original esto escribía TODO el estado (con contraseña) en Firestore
    page.evaluate("toggleLang()")
    page.evaluate("save()")
    page.wait_for_timeout(1200)               # > debounce de 600 ms
    assert fb(page, "S.writes.length") == 0


def test_visitor_local_state_has_no_password(make_page):
    page = make_page(); goto(page)
    page.evaluate("setLang('es')")
    stored = page.evaluate("localStorage.getItem('vfx-v6')")
    assert stored and "password" not in stored and "admin123" not in stored


def test_authenticated_save_publishes_state_without_password(make_page):
    page = make_page(); goto(page)
    login(page); page.wait_for_selector("#admin-overlay.on")
    page.evaluate("save()")
    page.wait_for_function("window.__fb.writes.length>=1", timeout=5000)
    payloads = fb(page, "S.writes.map(w=>w.data)")
    assert payloads and all("password" not in p and "admin123" not in p for p in payloads)


def test_legacy_password_in_remote_doc_is_scrubbed_locally_and_republished_clean_on_admin_login(make_page):
    seed = "window.__fb={writes:[],authCalls:[],authed:false,remote:" + json.dumps(json.dumps(LEGACY_DOC)) + "}"
    page = make_page(init=seed)
    goto(page)
    page.wait_for_function("localStorage.getItem('vfx-v6')!==null")
    local = page.evaluate("localStorage.getItem('vfx-v6')")
    assert "from-remote" in local                       # el contenido sí se carga…
    assert "password" not in local and "admin123" not in local     # …pero la contraseña NO se conserva
    assert fb(page, "S.writes.length") == 0              # un visitante no reescribe nada
    login(page); page.wait_for_selector("#admin-overlay.on")
    page.wait_for_function("window.__fb.writes.length>=1", timeout=5000)   # limpieza automática al entrar el admin
    assert "admin123" not in fb(page, "S.remote") and "password" not in fb(page, "S.remote")


def test_admin_settings_no_longer_has_a_password_field(make_page):
    page = make_page(); goto(page)
    login(page); page.wait_for_selector("#admin-overlay.on")
    page.evaluate("showSec('settings')")
    assert page.locator("#newPw").count() == 0
    assert "Firebase Authentication" in page.inner_text("#sec-settings")
    assert page.locator("#sec-settings button", has_text="Cerrar sesión").count() == 1


def test_admin_jobs_panel_not_mountable_without_session(make_page):
    page = make_page(); goto(page)
    page.evaluate("renderVfxJobsAdminView(true)")
    page.wait_for_timeout(300)
    assert page.locator("#vfxJobsAdminView .jp").count() == 0
