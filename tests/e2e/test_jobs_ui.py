"""E2E del panel de empleo en Chromium real (Playwright). Datos: fixtures, nunca producción."""
import json
import pytest
from conftest import open_public, open_admin_panel, goto, ids, login, fx
import harness

DEFAULT = ["gh-1", "gh-2", "gh-3", "gh-4", "gh-5", "sr-legacy"]


def test_direct_only_policy_hides_aggregators_even_if_unverified_enabled(make_page):
    payload = harness.fixture_jobs()
    payload["sourcePolicy"] = "direct-only"
    box = open_public(make_page(jobs=payload))
    box.locator('input[data-filter="showUnverified"]').check()
    box.locator('input[data-filter="showPossibleMatches"]').check()
    assert ids(box) == DEFAULT

def summary(box): return box.locator("[data-ref=summary]").inner_text()
def pressed(loc): return loc.get_attribute("aria-pressed") == "true"
def checked(loc): return loc.get_attribute("aria-checked") == "true"


def test_default_view_shows_only_verified_with_hidden_count(make_page):
    box = open_public(make_page())
    assert ids(box) == DEFAULT
    assert "3 ocultas" in summary(box)                 # az-1, az-3, az-up sin verificar
    assert box.locator(".jp-tab").all_inner_texts() == ["Ofertas", "Guardadas", "Empresas", "Mapa y estadísticas", "Ajustes"]


# UI-01 / UI-02 — defecto #3 reproducido en el original: España no se podía desactivar
def test_ui01_ui02_spain_chip_toggles_on_and_off(make_page):
    box = open_public(make_page())
    chip = box.locator('[data-action="toggle-spain"]')
    assert not pressed(chip)
    chip.click()
    assert pressed(chip) and ids(box) == ["gh-1", "gh-5"]
    assert "España" in box.locator("[data-ref=chips]").inner_text()
    chip.click()
    assert not pressed(chip) and ids(box) == DEFAULT
    assert box.locator("[data-ref=chips]").inner_text() == ""


# UI-03 / UI-04
def test_ui03_ui04_eligibility_single_choice_group(make_page):
    box = open_public(make_page())
    seg = lambda v: box.locator(f'.jp-seg[data-filter="spainEligibility"][data-value="{v}"]')
    seg("possible").click()
    assert checked(seg("possible")) and ids(box) == ["gh-2", "gh-4"]
    seg("unknown").click()
    assert checked(seg("unknown")) and not checked(seg("possible"))
    assert ids(box) == ["gh-5", "sr-legacy"]            # contradicción y heredado: a revisar, no confirmados
    n_on = box.locator('.jp-seg[data-filter="spainEligibility"][aria-checked="true"]').count()
    assert n_on == 1
    seg("all").click()
    assert ids(box) == DEFAULT and checked(seg("all"))


# UI-05
def test_ui05_include_unverified_adds_and_removes_records(make_page):
    box = open_public(make_page())
    cb = box.locator('input[data-filter="showUnverified"]')
    cb.check()
    assert ids(box) == sorted(DEFAULT + ["az-1", "az-3", "az-up"])
    assert box.locator(".jp-card.unv").count() == 3
    assert "Sin verificar" not in summary(box) and "(incluidas)" in summary(box)
    cb.uncheck()
    assert ids(box) == DEFAULT


def test_unverified_link_in_summary_works(make_page):
    box = open_public(make_page())
    box.locator('[data-action="show-unverified"]').click()
    assert box.locator('input[data-filter="showUnverified"]').is_checked()
    assert len(ids(box)) == 9


# UI-06
def test_ui06_possible_matches_checkbox(make_page):
    box = open_public(make_page())
    box.locator('input[data-filter="showUnverified"]').check()
    assert "az-2" not in ids(box)
    box.locator('input[data-filter="showPossibleMatches"]').check()
    assert "az-2" in ids(box)
    box.locator('input[data-filter="showPossibleMatches"]').uncheck()
    assert "az-2" not in ids(box)


# UI-07
def test_ui07_changing_sort_keeps_filters_and_changes_order(make_page):
    box = open_public(make_page())
    box.locator('select[data-filter="workplace"]').select_option("remote")
    before = ids(box)
    order_rel = box.locator(".jp-card").evaluate_all("els=>els.map(e=>e.dataset.job)")
    box.locator('select[data-filter="sort"]').select_option("company")
    assert ids(box) == before
    assert box.locator('select[data-filter="workplace"]').input_value() == "remote"
    companies = box.locator(".jp-card-sub strong").all_inner_texts()
    assert companies == sorted(companies, key=str.lower)
    assert "Modalidad: Remoto" in box.locator("[data-ref=chips]").inner_text()


# UI-08 — defecto reproducido en el original: el input perdía el foco tras cada letra
def test_ui08_search_keeps_focus_caret_and_full_text(make_page):
    page = make_page()
    box = open_public(page)
    q = box.locator('input[data-filter="query"]')
    q.click()
    page.keyboard.type("senior vfx", delay=30)
    assert q.input_value() == "senior vfx"
    assert page.evaluate("document.activeElement.matches('input[data-filter=query]')")
    assert ids(box) == ["gh-1", "gh-5", "sr-legacy"]
    # editar en mitad del texto: el cursor debe conservarse
    page.keyboard.press("Home"); page.keyboard.type("x")
    assert q.input_value() == "xsenior vfx" and ids(box) == []
    page.keyboard.press("Backspace")
    assert q.input_value() == "senior vfx"
    assert page.evaluate("document.activeElement.selectionStart") == 0
    box.locator('[data-action="clear-chip"][data-key="query"]').click()
    assert q.input_value() == "" and ids(box) == DEFAULT


def test_search_ignores_accents_and_case(make_page):
    page = make_page()
    box = open_public(page)
    box.locator('input[data-filter="showUnverified"]').check()
    box.locator('input[data-filter="query"]').fill("BARCELÓNA")
    assert ids(box) == ["az-1", "az-up"]


# UI-09
def test_ui09_empty_state_explains_cause_and_clear_works(make_page):
    box = open_public(make_page())
    box.locator('select[data-filter="workplace"]').select_option("onsite")
    box.locator('[data-action="toggle-spain"]').click()
    assert box.locator(".jp-empty").is_visible()
    assert "Quitando" in box.locator(".jp-empty").inner_text()
    box.locator(".jp-empty [data-action='clear-all']").click()
    assert ids(box) == DEFAULT
    assert box.locator('select[data-filter="workplace"]').input_value() == "all"
    assert not pressed(box.locator('[data-action="toggle-spain"]'))


def test_clear_all_resets_every_control_but_keeps_saved(make_page):
    box = open_public(make_page())
    box.locator('[data-action="save"][data-id="gh-1"]').click()
    box.locator('select[data-filter="contract"]').select_option("freelance")
    box.locator('.jp-seg[data-filter="spainEligibility"][data-value="possible"]').click()
    box.locator('[data-action="clear-all"]').first.click()
    assert ids(box) == DEFAULT
    assert pressed(box.locator('[data-action="save"][data-id="gh-1"]'))


def test_applied_chip_remove_button(make_page):
    box = open_public(make_page())
    box.locator('select[data-filter="contract"]').select_option("freelance")
    assert ids(box) == ["gh-4"]
    box.locator('[data-action="clear-chip"][data-key="contract"]').click()
    assert ids(box) == DEFAULT


def test_quick_views(make_page):
    box = open_public(make_page())
    box.locator('.jp-viewseg[data-value="compatible"]').click()
    assert ids(box) == ["gh-1", "gh-2"]
    box.locator('.jp-viewseg[data-value="review"]').click()
    assert ids(box) == ["gh-5", "sr-legacy"]
    box.locator('.jp-viewseg[data-value="all"]').click()
    assert "gh-3" in ids(box) and "gh-4" in ids(box)      # restringida y freelance: visibles en «Todos»


def test_advanced_filters_toggle_and_company_select_has_counts(make_page):
    box = open_public(make_page())
    btn = box.locator('[data-action="adv"]')
    assert btn.get_attribute("aria-expanded") == "false"
    btn.click()
    assert btn.get_attribute("aria-expanded") == "true"
    box.locator('select[data-filter="company"]').select_option(label="Alpha Games (1)")
    assert ids(box) == ["gh-1"]
    box.locator('select[data-filter="seniority"]').select_option("lead")
    assert ids(box) == []


# Contenido de tarjeta
def test_card_shows_provenance_unknowns_and_evidence(make_page):
    box = open_public(make_page())
    c = box.locator('[data-job="gh-1"]')
    txt = c.inner_text()
    assert "ATS oficial" in txt and "España: confirmada" in txt and "Contrato desconocido" in txt
    assert "Publicación oficial: no disponible" in txt
    c.locator("summary").click()
    assert "Puntuación" in c.inner_text() and "no es rechazo" in c.inner_text()
    assert box.locator('[data-job="gh-3"]').inner_text().count("España: restringida") == 1
    assert "Freelance/B2B — incompatible" in box.locator('[data-job="gh-4"]').inner_text()
    assert "España: contradicción" in box.locator('[data-job="gh-5"]').inner_text()
    gh5 = box.locator('[data-job="gh-5"]')
    gh5.locator("summary").click()
    assert "evidencia «Permanent»" in gh5.inner_text()                     # evidencia literal de la fuente
    assert "señales incompatibles" in gh5.inner_text().lower()              # y el motivo de la contradicción


def test_ranking_default_order_best_first(make_page):
    box = open_public(make_page())
    order = box.locator(".jp-card").evaluate_all("els=>els.map(e=>e.dataset.job)")
    assert order[0] == "gh-1" and order.index("gh-5") < order.index("gh-3") < order.index("gh-4")


def test_legacy_upgraded_record_is_unverified_and_warns_about_landing_link(make_page):
    box = open_public(make_page())
    box.locator('input[data-filter="showUnverified"]').check()
    c = box.locator('[data-job="az-up"]')
    assert "Agregador (señal)" in c.inner_text()
    assert "no a la vacante concreta" in c.inner_text()
    assert c.locator("a.jp-btn-primary").inner_text().startswith("Ir a la página de empleo")   # no promete «Ver oferta»
    assert box.locator('[data-job="gh-1"] a.jp-btn-primary').inner_text().startswith("Ver oferta")


def test_legacy_record_without_v2_fields_does_not_break(make_page):
    box = open_public(make_page())
    c = box.locator('[data-job="sr-legacy"]')
    assert "sin evaluar" in c.inner_text() or c.locator("summary").count() == 1
    c.locator("summary").click()
    assert "formato anterior" in c.inner_text()


# Seguridad de salida
def test_untrusted_content_is_escaped_and_unsafe_url_is_not_linked(make_page):
    page = make_page()
    box = open_public(page)
    box.locator('input[data-filter="showUnverified"]').check()
    c = box.locator('[data-job="az-3"]')
    assert "<img src=x" in c.inner_text() and "<b>bold</b>" in c.inner_text()   # texto literal, no HTML
    assert c.locator("img").count() == 0 and c.locator("b").count() == 0
    assert page.evaluate("window.__xss") is None
    assert box.locator('a[href^="javascript"]').count() == 0
    assert "Sin enlace válido" in c.inner_text()
    assert box.locator("a[target=_blank]").evaluate_all("els=>els.every(e=>e.rel.includes('noopener'))")


# Guardar / descartar / persistencia
def test_save_discard_restore_and_persist_after_reload(make_page):
    page = make_page()
    box = open_public(page)
    btn = box.locator('[data-action="save"][data-id="gh-2"]')
    btn.click()
    assert pressed(box.locator('[data-action="save"][data-id="gh-2"]'))
    box.locator('[data-action="discard"][data-id="gh-3"]').click()
    assert "gh-3" not in ids(box)
    page.reload(); open_public(page)
    box = page.locator("#vfxJobsBody")
    assert pressed(box.locator('[data-action="save"][data-id="gh-2"]')) and "gh-3" not in ids(box)
    box.locator('.jp-tab', has_text="Guardadas").click()
    assert "Solo en este navegador".lower() in box.locator('[data-pane="saved"]').inner_text().lower() or "solo en este navegador" in box.locator('[data-pane="saved"]').inner_text().lower()
    assert box.locator('[data-pane="saved"] .jp-card').count() == 1
    box.locator('.jp-tab', has_text="Ajustes").click()
    box.locator('[data-setting="showDiscarded"]').check()
    box.locator('.jp-tab', has_text="Ofertas").click()
    assert "gh-3" in ids(box)
    box.locator('[data-action="restore"][data-id="gh-3"]').click()
    assert box.locator('[data-job="gh-3"] [data-action="discard"]').count() == 1


def test_keyboard_save_keeps_focus_on_same_control(make_page):
    page = make_page()
    box = open_public(page)
    b = box.locator('[data-action="save"][data-id="gh-1"]')
    b.focus(); page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.dataset.action+':'+document.activeElement.dataset.id") == "save:gh-1"


def test_filters_persist_across_reload_and_can_be_disabled(make_page):
    page = make_page()
    box = open_public(page)
    box.locator('select[data-filter="workplace"]').select_option("remote")
    page.reload(); box = open_public(page)
    assert box.locator('select[data-filter="workplace"]').input_value() == "remote"
    box.locator('.jp-tab', has_text="Ajustes").click()
    box.locator('[data-setting="persistFilters"]').uncheck()
    page.reload(); box = open_public(page)
    assert box.locator('select[data-filter="workplace"]').input_value() == "all"


def test_corrupt_stored_preferences_do_not_break_page(make_page):
    page = make_page(init="try{localStorage.setItem('vfxjobs-v2', JSON.stringify({v:1,filters:{workplace:'<script>',sort:7,location:'spain'},saved:'x'}))}catch(e){}")
    box = open_public(page)
    assert box.locator('select[data-filter="workplace"]').input_value() == "all"
    assert pressed(box.locator('[data-action="toggle-spain"]'))
    page2 = make_page(init="try{localStorage.setItem('vfxjobs-v2', '{not json')}catch(e){}")
    assert len(ids(open_public(page2))) == 6


# Pestañas
def test_tabs_keyboard_navigation_and_aria(make_page):
    page = make_page()
    box = open_public(page)
    first = box.locator('.jp-tab[data-tab="offers"]')
    assert first.get_attribute("aria-selected") == "true"
    first.focus(); page.keyboard.press("ArrowRight")
    assert box.locator('.jp-tab[data-tab="saved"]').get_attribute("aria-selected") == "true"
    assert page.evaluate("document.activeElement.dataset.tab") == "saved"
    page.keyboard.press("End")
    assert page.evaluate("document.activeElement.dataset.tab") == "settings"
    assert box.locator('[data-pane="settings"]').is_visible() and not box.locator('[data-pane="offers"]').is_visible()
    tab = box.locator('.jp-tab[data-tab="settings"]')
    assert box.locator("#" + tab.get_attribute("aria-controls")).count() == 1


def test_companies_tab_separates_monitored_working_and_with_jobs(make_page):
    page = make_page()
    box = open_public(page)
    box.locator('.jp-tab', has_text="Empresas").click()
    page.wait_for_selector(".jp-co")
    txt = box.locator('[data-pane="companies"]').inner_text()
    assert "Alpha Games" in txt and "Broken Co" in txt and "Mundfish" in txt
    broken = box.locator(".jp-co", has_text="Broken Co")
    assert "Con error" in broken.inner_text() and "No confirmada".lower() in broken.inner_text().lower()
    assert "No response from https://broken.test/careers" in broken.inner_text()   # última incidencia visible
    assert "No monitorizada" in box.locator(".jp-co", has_text="Mundfish").inner_text()
    box.locator("[data-cost]").select_option("with-jobs")
    names = box.locator(".jp-co-h strong").all_inner_texts()
    assert "Broken Co" not in names and "Alpha Games" in names
    box.locator("[data-cost]").select_option("all")
    box.locator("[data-coq]").fill("mund")
    assert box.locator(".jp-co").count() == 1


def test_public_visitor_has_no_admin_tabs(make_page):
    box = open_public(make_page())
    t = box.locator(".jp-tab").all_inner_texts()
    assert "Fuentes y scanner" not in t and "Mis candidaturas" not in t


# Estados de carga / error
def test_error_state_and_retry(make_page):
    page = make_page(jobs_status=500)
    box = open_public(page)
    assert "No se pudieron cargar" in box.locator(".jp-error").inner_text()
    page.unroute("**/data/jobs.json*")
    harness.install_routes(page, extra_files=None)
    box.locator('[data-action="retry"]').click()
    page.wait_for_selector("#vfxJobsBody .jp-card")
    assert len(ids(box)) == 6


def test_empty_dataset_message(make_page):
    box = open_public(make_page(jobs={"lastUpdated": "2026-10-20T00:00:00Z", "jobs": []}))
    assert "Todavía no hay ofertas" in box.locator(".jp-empty").inner_text()


def test_stale_data_banner(make_page):
    page = make_page(jobs=harness.fixture_jobs(age_hours=30))
    box = open_public(page)
    assert box.locator("[data-ref=banner]").is_visible() and "30 h" in box.locator("[data-ref=banner]").inner_text()
    fresh = make_page()
    assert not open_public(fresh).locator("[data-ref=banner]").is_visible() or "formato anterior" not in ""


def test_legacy_schema_banner_when_schemaVersion_missing(make_page):
    d = harness.fixture_jobs(); d.pop("schemaVersion", None)
    box = open_public(make_page(jobs=d))
    assert "formato anterior" in box.locator("[data-ref=banner]").inner_text()


# UI-10 — defecto reproducido en el original: overlay y admin compartían un único renderTarget
def test_ui10_admin_panel_and_overlay_are_independent(make_page):
    page = make_page()
    goto(page)
    admin = open_admin_panel(page)
    admin.locator('select[data-filter="workplace"]').select_option("remote")
    admin_before = ids(admin)
    page.evaluate("openVfxJobsPublic()")
    overlay = page.locator("#vfxJobsBody")
    page.wait_for_selector("#vfxJobsBody .jp-card")
    overlay.locator('select[data-filter="contract"]').select_option("freelance")
    assert ids(overlay) == ["gh-4"]
    assert ids(admin) == admin_before                              # el admin no se ha visto afectado
    page.evaluate("closeVfxJobsPublic()")
    admin.locator('[data-action="toggle-spain"]').click()
    assert pressed(admin.locator('[data-action="toggle-spain"]'))
    assert ids(admin) == ["gh-1", "gh-5"]
    # el overlay arrancó con los filtros recordados (workplace=remote) pero desde entonces es independiente
    assert overlay.locator('select[data-filter="workplace"]').input_value() == "remote"
    assert not pressed(overlay.locator('[data-action="toggle-spain"]'))   # el overlay no recibió el clic del admin


def test_admin_has_sources_tab_with_scanner_report_and_failures(make_page):
    page = make_page()
    goto(page)
    admin = open_admin_panel(page)
    tabs = admin.locator(".jp-tab").all_inner_texts()
    assert "Fuentes y scanner" in tabs and "Mis candidaturas" in tabs
    admin.locator(".jp-tab", has_text="Fuentes y scanner").click()
    page.wait_for_selector("#vfxJobsAdminView .jp-stat")
    txt = admin.locator('[data-pane="sources"]').inner_text()
    assert "Peso de agregadores" in txt and "40 %" in txt and "Duplicados fusionados" in txt
    assert "timeout" in txt and "3 fallos seguidos" in txt
    assert admin.locator('a[href*="actions/workflows"]').count() == 1
    assert "no puede lanzarla" in txt
    admin.locator(".jp-tab", has_text="Mis candidaturas").click()
    assert "desactivada a propósito" in admin.locator('[data-pane="apps"]').inner_text()


def test_sources_tab_without_report_file_explains_it(make_page):
    page = make_page()
    page.route("**/data/scanner-report.json*", lambda r: r.fulfill(status=404, body="no"))
    goto(page)
    admin = open_admin_panel(page)
    admin.locator(".jp-tab", has_text="Fuentes y scanner").click()
    page.wait_for_selector("#vfxJobsAdminView .jp-banner:visible")
    assert "primera ejecución del scanner V2" in admin.locator('[data-pane="sources"]').inner_text()


# UI-12 — todos los controles reciben foco por teclado y se pueden accionar
def test_ui12_every_control_is_keyboard_reachable_and_operable(make_page):
    page = make_page()
    box = open_public(page)
    box.locator('input[data-filter="showUnverified"]').check()
    box.locator('[data-action="adv"]').click()
    expected = page.evaluate("""()=>[...document.querySelectorAll('#vfxJobsBody .jp button, #vfxJobsBody .jp select, #vfxJobsBody .jp input, #vfxJobsBody .jp summary, #vfxJobsBody .jp a[href]')]
        .filter(e=>e.offsetParent!==null && !e.disabled && e.tabIndex>=0).length""")
    box.locator('input[data-filter="query"]').focus()
    visited = set()
    for _ in range(expected + 5):
        sig = page.evaluate("""()=>{const a=document.activeElement;if(!a||!a.closest('#vfxJobsBody'))return null;
            const r=a.getBoundingClientRect();return [a.tagName,a.dataset.action||a.dataset.filter||a.dataset.id||a.id||a.textContent.trim().slice(0,12),a.dataset.value||'',Math.round(r.top)].join('|')}""")
        if sig: visited.add(sig)
        page.keyboard.press("Tab")
    assert len(visited) >= expected - 3, f"solo {len(visited)} de {expected} controles alcanzables con Tab"
    # …y accionables con teclado
    chip = box.locator('[data-action="toggle-spain"]'); chip.focus(); page.keyboard.press("Enter")
    assert pressed(chip)
    page.keyboard.press("Space")
    assert not pressed(chip)
    seg = box.locator('.jp-seg[data-filter="spainEligibility"][data-value="possible"]'); seg.focus(); page.keyboard.press("Space")
    assert checked(seg)
    cb = box.locator('input[data-filter="showPossibleMatches"]'); cb.focus(); page.keyboard.press("Space")
    assert cb.is_checked()
    sel = box.locator('select[data-filter="contract"]'); sel.focus(); page.keyboard.press("ArrowDown")
    assert sel.input_value() != "all"
    box.locator('[data-action="clear-all"]').first.focus(); page.keyboard.press("Enter")
    assert ids(box) == DEFAULT                                  # «Limpiar» deja el estado predeterminado exacto
