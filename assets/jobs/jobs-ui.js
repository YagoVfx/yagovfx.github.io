/*
 * jobs-ui.js — interfaz del panel de empleo (V2).
 *
 * Causas raíz que corrige respecto al módulo anterior (ver AUDITORIA_V2.md):
 *  - El render reescribía TODO el panel con innerHTML (incluido el <input> de
 *    búsqueda) en cada pulsación → perdía foco y cursor. Ahora los controles se
 *    crean UNA vez; solo se vuelven a pintar resumen, chips y lista.
 *  - Un único `renderTarget` global compartido por overlay y admin hacía que, tras
 *    usar uno, los controles del otro dibujaran en el contenedor equivocado.
 *    Ahora cada instancia tiene su propio contenedor y su propio estado.
 *  - setVfxLocationFilter asignaba siempre el mismo valor (España no se podía
 *    desactivar). Ahora es un toggle explícito en la función pura toggleSpain().
 *  - Todo texto externo se escapa y las URL se limitan a http/https.
 */
(function (root) {
  'use strict';
  var C = root.VfxJobsCore;
  if (!C) { console.error('[jobs-ui] Falta VfxJobsCore'); return; }
  var esc = C.escapeHtml, L = C.LABELS;

  var PREF_KEY = 'vfxjobs-v2';
  var DATA = {
    jobs: 'data/jobs.json', companies: 'data/companies.json', status: 'data/scanner-status.json',
    report: 'data/scanner-report.json', registry: 'data/companies-registry.json',
    world: 'data/world-map.json', locations: 'data/company-locations.json'
  };
  var WORKFLOW_URL = 'https://github.com/YagoVfx/yagovfx.github.io/actions/workflows/vfx-jobs-scanner.yml';
  var PAGE = 50;
  var seq = 0;
  var panels = [];

  // ───────────────────────── preferencias locales (versionadas) ─────────────────────────
  function readPrefs() {
    var p = { v: 1, saved: {}, savedMeta: {}, discarded: {}, filters: null, settings: { persistFilters: true, showDiscarded: false } };
    try {
      var s = JSON.parse(localStorage.getItem(PREF_KEY) || 'null');
      if (s && s.v === 1) {
        ['saved', 'savedMeta', 'discarded'].forEach(function (k) { if (s[k] && typeof s[k] === 'object') p[k] = s[k]; });
        if (s.filters && typeof s.filters === 'object') p.filters = s.filters;
        if (s.settings && typeof s.settings === 'object') {
          p.settings.persistFilters = s.settings.persistFilters !== false;
          p.settings.showDiscarded = s.settings.showDiscarded === true;
        }
      }
    } catch (e) { /* almacenamiento no disponible: se trabaja en memoria */ }
    return p;
  }
  function writePrefs(p) { try { localStorage.setItem(PREF_KEY, JSON.stringify(p)); } catch (e) { /* ignorar */ } }

  // ───────────────────────── carga de datos con caché ─────────────────────────
  var cache = {};
  function loadJson(key, force) {
    if (!force && cache[key]) return cache[key];
    cache[key] = fetch(DATA[key], { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error(key + ' HTTP ' + r.status);
      return r.json();
    });
    cache[key].catch(function () { delete cache[key]; });
    return cache[key];
  }
  function softJson(key, force) { return loadJson(key, force).catch(function () { return null; }); }

  // ───────────────────────── Panel ─────────────────────────
  function Panel(el, opts) {
    this.el = el; this.opts = opts || {};
    this.admin = !!this.opts.admin;
    this.uid = 'jp' + (++seq);
    this.prefs = readPrefs();
    var stored = this.prefs.settings.persistFilters ? this.prefs.filters : null;
    this.filters = C.sanitizeFilters(stored);
    this.filters.query = '';
    this.tab = 'offers';
    this.limit = PAGE;
    this.jobs = []; this.raw = null; this.loaded = false; this.error = null;
    this.extra = {};
    this.refocus = null;
    this.build();
    this.bind();
    this.load(false);
    panels.push(this);
    if(root.VfxApplications){var panel=this;root.VfxApplications.subscribe(function(){panel.renderList();if(panel.tab==='apps')panel.renderApps();});}
  }

  Panel.prototype.id = function (n) { return this.uid + '-' + n; };

  Panel.prototype.build = function () {
    var u = this.id.bind(this);
    var tabs = [['offers', 'Ofertas'], ['saved', 'Guardadas'], ['companies', 'Empresas'], ['insights', 'Mapa y estadísticas']];
    tabs.push(['apps', 'Mis candidaturas']);
    if (this.admin) tabs.push(['sources', 'Fuentes y scanner']);
    tabs.push(['settings', 'Ajustes']);
    this.tabIds = tabs.map(function (t) { return t[0]; });

    var tabBtns = tabs.map(function (t, i) {
      return '<button type="button" role="tab" class="jp-tab" id="' + u('tab-' + t[0]) + '" data-action="tab" data-tab="' + t[0] + '"' +
        ' aria-controls="' + u('panel-' + t[0]) + '" aria-selected="' + (i === 0 ? 'true' : 'false') + '" tabindex="' + (i === 0 ? '0' : '-1') + '">' + esc(t[1]) + '</button>';
    }).join('');

    function opt(map, keys, allLabel) {
      return '<option value="all">' + allLabel + '</option>' + keys.map(function (k) { return '<option value="' + k + '">' + esc(map[k]) + '</option>'; }).join('');
    }
    function sel(key, label, inner) {
      return '<div class="jp-field"><label for="' + u('f-' + key) + '">' + label + '</label>' +
        '<select id="' + u('f-' + key) + '" data-filter="' + key + '">' + inner + '</select></div>';
    }
    var elig = [['all', 'Todas'], ['confirmed', 'Confirmada'], ['possible', 'Posible'], ['unknown', 'Sin confirmar'], ['restricted', 'Restringida']]
      .map(function (o) {
        return '<button type="button" role="radio" class="jp-seg" data-filter="spainEligibility" data-value="' + o[0] + '" aria-checked="' + (o[0] === 'all' ? 'true' : 'false') + '">' + o[1] + '</button>';
      }).join('');
    var views = ['all', 'compatible', 'review', 'saved'].map(function (v) {
      return '<button type="button" role="radio" class="jp-seg jp-viewseg" data-filter="view" data-value="' + v + '" aria-checked="' + (v === 'all' ? 'true' : 'false') + '">' + L.view[v] + '</button>';
    }).join('');

    this.el.classList.add('jp');
    this.el.setAttribute('data-mode', this.admin ? 'admin' : 'public');
    this.el.innerHTML =
      '<div class="jp-head"><h2 class="jp-title">Empleo VFX</h2><p class="jp-updated" data-ref="updated">Cargando…</p></div>' +
      '<p class="jp-scanner-link"><a class="jp-btn" href="' + WORKFLOW_URL + '" target="_blank" rel="noopener noreferrer">Jobs VFX Scanner en GitHub ↗</a></p>' +
      '<div class="jp-banner" data-ref="banner" hidden></div>' +
      '<div class="jp-tabs" role="tablist" aria-label="Secciones del panel de empleo">' + tabBtns + '</div>' +

      // ── Ofertas ──
      '<section class="jp-pane" role="tabpanel" id="' + u('panel-offers') + '" aria-labelledby="' + u('tab-offers') + '" data-pane="offers">' +
        '<div class="jp-search"><label for="' + u('q') + '" class="jp-vh">Buscar cargo, empresa o herramienta</label>' +
          '<input id="' + u('q') + '" data-filter="query" type="search" autocomplete="off" placeholder="Buscar cargo, empresa, herramienta…" maxlength="120"></div>' +
        '<div class="jp-segs" role="radiogroup" aria-label="Vista de ofertas">' + views + '</div>' +
        '<p class="jp-summary" role="status" aria-live="polite" data-ref="summary"></p>' +
        '<div class="jp-main">' +
          sel('workplace', 'Modalidad', opt(L.workplace, ['remote', 'hybrid', 'onsite', 'unknown'], 'Cualquiera')) +
          sel('contract', 'Contrato', opt(L.contract, ['employee', 'freelance', 'temporary', 'unknown'], 'Cualquiera')) +
          sel('sort', 'Ordenar por', ['relevance', 'recent', 'company', 'title', 'verified'].map(function (k) { return '<option value="' + k + '">' + esc(L.sort[k]) + '</option>'; }).join('')) +
        '</div>' +
        '<div class="jp-group"><span class="jp-grouplabel" id="' + u('elig-l') + '">Compatibilidad con España</span>' +
          '<div class="jp-segs" role="radiogroup" aria-labelledby="' + u('elig-l') + '">' + elig + '</div></div>' +
        '<div class="jp-toggles">' +
          '<button type="button" class="jp-chip" data-action="toggle-spain" aria-pressed="false">🇪🇸 España</button>' +
          '<button type="button" class="jp-chip" data-action="toggle-eu" aria-pressed="false" title="Ubicación o ámbito de la Unión Europea explícitos; Europa genérica no basta">🇪🇺 Unión Europea</button>' +
          '<label class="jp-check"><input type="checkbox" data-filter="showUnverified"> <span data-ref="lblUnverified">Incluir sin verificar</span></label>' +
          '<label class="jp-check"><input type="checkbox" data-filter="showPossibleMatches"> <span>Incluir coincidencias posibles</span></label>' +
        '</div>' +
        '<div class="jp-advtoggle"><button type="button" class="jp-btn" data-action="adv" aria-expanded="false" aria-controls="' + u('adv') + '">Filtros avanzados <span aria-hidden="true">▾</span></button>' +
          '<button type="button" class="jp-btn jp-btn-ghost" data-action="clear-all">Limpiar filtros</button></div>' +
        '<div class="jp-adv" id="' + u('adv') + '" hidden>' +
          sel('seniority', 'Nivel', opt(L.seniority, ['junior', 'mid', 'senior', 'lead', 'unknown'], 'Cualquiera')) +
          sel('role', 'Rol', opt(L.role, ['vfx', 'tech-vfx', 'technical-artist', 'other'], 'Cualquiera')) +
          sel('engine', 'Motor', opt(L.engine, ['unreal', 'unity', 'houdini', 'proprietary'], 'Cualquiera')) +
          sel('company', 'Empresa', '<option value="all">Todas</option>') +
          sel('studioType', 'Tipo de estudio', opt(L.studioType, ['aaa', 'indie', 'unknown'], 'Cualquiera')) +
          sel('ats', 'ATS / fuente', '<option value="all">Todas</option>') +
          sel('location', 'Ubicación', '<option value="all">Todas</option>') +
          sel('dateRange', 'Fecha', opt(L.dateRange, ['7', '30', '90'], 'Cualquiera')) +
          sel('hours', 'Jornada', opt(L.hours, ['full', 'part', 'unknown'], 'Cualquiera')) +
        '</div>' +
        '<div class="jp-chips" data-ref="chips" aria-label="Filtros aplicados"></div>' +
        '<ul class="jp-list" data-ref="list" aria-label="Resultados"></ul>' +
        '<div class="jp-more" data-ref="more"></div>' +
      '</section>' +

      '<section class="jp-pane" role="tabpanel" id="' + u('panel-saved') + '" aria-labelledby="' + u('tab-saved') + '" data-pane="saved" hidden></section>' +
      '<section class="jp-pane" role="tabpanel" id="' + u('panel-companies') + '" aria-labelledby="' + u('tab-companies') + '" data-pane="companies" hidden></section>' +
      '<section class="jp-pane" role="tabpanel" id="' + u('panel-insights') + '" aria-labelledby="' + u('tab-insights') + '" data-pane="insights" hidden></section>' +
      '<section class="jp-pane" role="tabpanel" id="' + u('panel-apps') + '" aria-labelledby="' + u('tab-apps') + '" data-pane="apps" hidden></section>' +
      (this.admin ?
        '<section class="jp-pane" role="tabpanel" id="' + u('panel-sources') + '" aria-labelledby="' + u('tab-sources') + '" data-pane="sources" hidden></section>' : '') +
      '<section class="jp-pane" role="tabpanel" id="' + u('panel-settings') + '" aria-labelledby="' + u('tab-settings') + '" data-pane="settings" hidden></section>';
  };

  Panel.prototype.ref = function (n) { return this.el.querySelector('[data-ref="' + n + '"]'); };
  Panel.prototype.pane = function (n) { return this.el.querySelector('[data-pane="' + n + '"]'); };

  // ───────────────────────── eventos (delegados, DOM estable) ─────────────────────────
  Panel.prototype.bind = function () {
    var self = this, el = this.el;
    el.addEventListener('click', function (e) {
      var seg = e.target.closest('.jp-seg[data-filter]');
      if (seg && el.contains(seg)) { self.setFilter(seg.getAttribute('data-filter'), seg.getAttribute('data-value')); return; }
      var t = e.target.closest('[data-action]');
      if (!t || !el.contains(t)) return;
      self.action(t.getAttribute('data-action'), t);
    });
    el.addEventListener('input', function (e) {
      var t = e.target;
      if (t.matches && t.matches('input[data-filter="query"]')) self.setFilter('query', t.value);
    });
    el.addEventListener('change', function (e) {
      var t = e.target;
      if (!t.matches) return;
      if (t.matches('select[data-filter]')) self.setFilter(t.getAttribute('data-filter'), t.value);
      else if (t.matches('input[type="checkbox"][data-filter]')) self.setFilter(t.getAttribute('data-filter'), t.checked);
      else if (t.matches('[data-setting]')) self.setSetting(t.getAttribute('data-setting'), t.checked);
      else if (t.matches('[data-coq], [data-cost], [data-coc]')) self.renderCompanies();
    });
    el.addEventListener('input', function (e) { if (e.target.matches && e.target.matches('[data-coq]')) self.renderCompanies(); });
    el.addEventListener('keydown', function (e) {
      var tab = e.target.closest && e.target.closest('[role="tab"]');
      if (!tab || !el.contains(tab)) return;
      var ids = self.tabIds, i = ids.indexOf(tab.getAttribute('data-tab')), n = null;
      if (e.key === 'ArrowRight') n = (i + 1) % ids.length;
      else if (e.key === 'ArrowLeft') n = (i - 1 + ids.length) % ids.length;
      else if (e.key === 'Home') n = 0; else if (e.key === 'End') n = ids.length - 1;
      if (n === null) return;
      e.preventDefault(); self.setTab(ids[n], true);
    });
  };

  Panel.prototype.action = function (a, t) {
    var id = t.getAttribute('data-id'), self=this;
    switch (a) {
      case 'tab': this.setTab(t.getAttribute('data-tab')); break;
      case 'toggle-spain': this.filters = C.toggleSpain(this.filters); this.afterFilterChange(); break;
      case 'toggle-eu': this.filters.location = this.filters.location === 'eu' ? 'all' : 'eu'; this.afterFilterChange(); break;
      case 'apply': {
        var job=this.jobs.find(function(j){return j.id===id;});
        if(!root.VfxPrivateAuth||!root.VfxPrivateAuth.user){this.setTab('apps');break;}
        if(job&&root.VfxApplications)root.VfxApplications.save(job,'applied').catch(function(err){self.setTab('apps');});
        break;
      }
      case 'application-details': this.setTab('apps'); break;
      case 'adv': this.toggleAdv(); break;
      case 'clear-all': this.clearAll(); break;
      case 'clear-chip': this.filters = C.clearFilter(this.filters, t.getAttribute('data-key')); this.afterFilterChange(); break;
      case 'more': this.limit += PAGE; this.renderList(); break;
      case 'save': this.toggleSaved(id, t); break;
      case 'discard': this.setDiscarded(id, true, t); break;
      case 'restore': this.setDiscarded(id, false, t); break;
      case 'retry': this.load(true); break;
      case 'reload': this.load(true); break;
      case 'clear-saved': this.prefs.saved = {}; this.prefs.savedMeta = {}; this.persist(); break;
      case 'clear-discarded': this.prefs.discarded = {}; this.persist(); break;
      case 'goto-offers': this.setTab('offers'); break;
      case 'show-unverified': this.setFilter('showUnverified', true); break;
    }
  };

  // ───────────────────────── estado ─────────────────────────
  Panel.prototype.setFilter = function (key, value) {
    var n = {}; for (var k in this.filters) n[k] = this.filters[k];
    n[key] = value;
    this.filters = C.sanitizeFilters(n);
    this.afterFilterChange(key === 'query');
  };
  Panel.prototype.afterFilterChange = function (typing) {
    this.limit = PAGE;
    this.savePrefsFilters();
    this.render(typing);
  };
  Panel.prototype.clearAll = function () {
    this.filters = C.sanitizeFilters(null);
    this.afterFilterChange();
    var q = this.el.querySelector('input[data-filter="query"]'); if (q) q.focus();
  };
  Panel.prototype.savePrefsFilters = function () {
    if (!this.prefs.settings.persistFilters) return;
    var f = {}; for (var k in this.filters) f[k] = this.filters[k];
    f.query = '';
    this.prefs.filters = f;
    writePrefs(this.prefs);
  };
  Panel.prototype.persist = function () {
    writePrefs(this.prefs);
    panels.forEach(function (p) { p.prefs = readPrefs(); p.renderAll(); });
  };
  Panel.prototype.setSetting = function (k, v) {
    this.prefs.settings[k] = v;
    if (k === 'persistFilters' && !v) this.prefs.filters = null;
    if (k === 'persistFilters' && v) this.savePrefsFilters();
    this.persist();
  };
  Panel.prototype.ctx = function () {
    return { now: Date.now(), saved: this.prefs.saved, discarded: this.prefs.discarded, showDiscarded: this.prefs.settings.showDiscarded };
  };
  Panel.prototype.toggleSaved = function (id, btn) {
    var j = this.jobs.filter(function (x) { return x.id === id; })[0];
    if (this.prefs.saved[id]) { delete this.prefs.saved[id]; delete this.prefs.savedMeta[id]; }
    else {
      this.prefs.saved[id] = true;
      if (j) this.prefs.savedMeta[id] = { title: j.title, company: j.company, url: j.safeUrl, savedAt: new Date().toISOString() };
    }
    this.refocus = '[data-action="save"][data-id="' + id + '"]';
    this.persist();
  };
  Panel.prototype.setDiscarded = function (id, on, btn) {
    if (on) this.prefs.discarded[id] = true; else delete this.prefs.discarded[id];
    this.refocus = on ? null : '[data-action="restore"][data-id="' + id + '"]';
    this.persist();
  };

  Panel.prototype.setTab = function (name, focus) {
    var self = this;
    this.tab = name;
    this.tabIds.forEach(function (t) {
      var b = self.el.querySelector('#' + self.id('tab-' + t)), p = self.pane(t);
      var on = t === name;
      b.setAttribute('aria-selected', on ? 'true' : 'false'); b.setAttribute('tabindex', on ? '0' : '-1');
      if (p) p.hidden = !on;
    });
    if (focus) this.el.querySelector('#' + this.id('tab-' + name)).focus();
    this.renderAll();
    if (name === 'companies') this.loadCompaniesData();
    if (name === 'insights') this.loadInsightsData();
    if (name === 'sources') this.loadSourcesData();
    if (name === 'apps' && root.VfxApplications) root.VfxApplications.refresh();
  };

  Panel.prototype.loadInsightsData = function () {
    var self = this, p = this.pane('insights');
    if (this.extra.insights) { this.renderInsights(); return; }
    p.innerHTML = '<div class="jp-state">Cargando mapa y estadísticas…</div>';
    Promise.all([loadJson('world'), loadJson('locations'), loadJson('companies')]).then(function(r) {
      self.extra.insights = {world:r[0],locations:r[1],companies:r[2]}; self.renderInsights();
    }).catch(function() { p.innerHTML='<div class="jp-state">No se pudo cargar el mapa. Vuelve a abrir esta pestaña para reintentar.</div>'; });
  };
  Panel.prototype.renderInsights = function () {
    var d=this.extra.insights;
    if(d && root.VfxJobsInsights) root.VfxJobsInsights.mount(this.pane('insights'),d,this.jobs,d.companies);
  };

  Panel.prototype.toggleAdv = function () {
    var b = this.el.querySelector('[data-action="adv"]'), box = this.el.querySelector('#' + this.id('adv'));
    var open = b.getAttribute('aria-expanded') !== 'true';
    b.setAttribute('aria-expanded', open ? 'true' : 'false'); box.hidden = !open;
  };

  // ───────────────────────── carga ─────────────────────────
  Panel.prototype.load = function (force) {
    var self = this;
    this.error = null; this.loaded = false;
    this.renderAll();
    return loadJson('jobs', force).then(function (data) {
      self.raw = data; self.jobs = C.normalizeJobs(data && data.jobs);
      if (data && data.sourcePolicy === 'direct-only') {
        self.jobs = self.jobs.filter(function (j) { return (j.sourceKind === 'ats' || j.sourceKind === 'official-site') && !/^(az-|sig-)/.test(j.id) && !j.viaAggregator; });
      }
      self.loaded = true;
      self.fillDataSelects(); self.renderAll();
    }).catch(function (err) {
      self.error = String(err && err.message || err); self.loaded = true; self.renderAll();
    });
  };
  Panel.prototype.loadCompaniesData = function () {
    var self = this;
    if (this.extra.companies) return;
    Promise.all([softJson('companies'), softJson('status'), softJson('registry')]).then(function (r) {
      self.extra.companies = { list: r[0] || [], status: r[1] || [], registry: r[2] };
      self.renderCompanies();
    });
  };
  Panel.prototype.loadSourcesData = function () {
    var self = this;
    if (this.extra.sources) return;
    Promise.all([softJson('report'), softJson('status')]).then(function (r) {
      self.extra.sources = { report: r[0], status: r[1] || [] };
      self.renderSources();
    });
  };

  Panel.prototype.fillDataSelects = function () {
    var jobs = this.jobs, f = this.filters, self = this;
    var ctx = this.ctx();
    function fill(key, getter, labeler) {
      var s = self.el.querySelector('select[data-filter="' + key + '"]');
      var counts = C.optionCounts(jobs, f, ctx, key, getter);
      var keys = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a] || a.localeCompare(b); });
      if (f[key] !== 'all' && keys.indexOf(f[key]) < 0 && !(key === 'location' && ['spain','eu'].indexOf(f[key])>=0)) keys.push(f[key]);
      var html = '<option value="all">Todas</option>';
      if (key === 'location') html += '<option value="spain">🇪🇸 España — todas (' + jobs.filter(function (j) { return j.status !== 'closed' && C.isSpain(j); }).length + ')</option>';
      if (key === 'location') html += '<option value="eu">🇪🇺 Unión Europea</option>';
      keys.forEach(function (k) { html += '<option value="' + esc(k) + '">' + esc(labeler ? labeler(k) : k) + ' (' + (counts[k] || 0) + ')</option>'; });
      if (s.getAttribute('data-sig') !== html) { s.innerHTML = html; s.setAttribute('data-sig', html); }
      s.value = f[key];
    }
    fill('company', function (j) { return j.company; });
    fill('ats', function (j) { return j.ats; });
    fill('location', function (j) { return j.location || 'Ubicación desconocida'; });
  };

  // ───────────────────────── render ─────────────────────────
  Panel.prototype.renderAll = function () {
    this.render();
    if (this.tab === 'saved') this.renderSaved();
    if (this.tab === 'companies') this.renderCompanies();
    if (this.tab === 'insights') this.renderInsights();
    if (this.tab === 'sources') this.renderSources();
    if (this.tab === 'apps') this.renderApps();
    if (this.tab === 'settings') this.renderSettings();
  };

  Panel.prototype.syncControls = function (typing) {
    var f = this.filters, el = this.el;
    el.querySelectorAll('[data-filter]').forEach(function (c) {
      var k = c.getAttribute('data-filter');
      if (c.classList.contains('jp-seg')) {
        var on = f[k] === c.getAttribute('data-value');
        c.setAttribute('aria-checked', on ? 'true' : 'false'); c.classList.toggle('on', on);
      } else if (c.type === 'checkbox') { if (c.checked !== !!f[k]) c.checked = !!f[k]; }
      else if (c.tagName === 'SELECT') { if (c.value !== f[k]) c.value = f[k]; }
      else if (k === 'query') { if (document.activeElement !== c && c.value !== f.query) c.value = f.query; }
    });
    var sp = el.querySelector('[data-action="toggle-spain"]');
    var spOn = f.location === 'spain';
    sp.setAttribute('aria-pressed', spOn ? 'true' : 'false'); sp.classList.toggle('on', spOn);
    var eu=el.querySelector('[data-action="toggle-eu"]');eu.setAttribute('aria-pressed',f.location==='eu'?'true':'false');eu.classList.toggle('on',f.location==='eu');
  };

  Panel.prototype.render = function (typing) {
    if (!this.pane('offers')) return;
    var upd = this.ref('updated'), banner = this.ref('banner');
    if (!this.loaded) { upd.textContent = 'Cargando…'; this.ref('list').innerHTML = '<li class="jp-state">Cargando ofertas…</li>'; this.ref('summary').textContent = ''; this.ref('chips').innerHTML = ''; this.ref('more').innerHTML = ''; this.syncControls(); return; }
    if (this.error) {
      upd.textContent = 'No disponible'; this.ref('summary').textContent = '';
      this.ref('chips').innerHTML = ''; this.ref('more').innerHTML = '';
      this.ref('list').innerHTML = '<li class="jp-state jp-error" role="alert">No se pudieron cargar las ofertas (' + esc(this.error) + '). ' +
        '<button type="button" class="jp-btn" data-action="retry">Reintentar</button></li>';
      this.syncControls(); return;
    }
    var data = this.raw || {};
    upd.textContent = 'Actualizado: ' + C.timeAgo(data.lastUpdated);
    var msgs = [];
    if (data.schemaVersion !== 2) msgs.push('Los datos están en formato anterior: la elegibilidad para España y el contrato aún no se han evaluado. Se completarán en la próxima ejecución del scanner.');
    var ageH = (Date.now() - Date.parse(data.lastUpdated || '')) / 3600000;
    if (isFinite(ageH) && ageH > 13) msgs.push('Los datos tienen más de ' + Math.floor(ageH) + ' h (el scanner corre cada 6 h): puede haber ofertas ya cerradas.');
    banner.hidden = !msgs.length; banner.textContent = msgs.join(' ');

    this.fillDataSelects();
    this.syncControls(typing);
    var ctx = this.ctx(), counts = C.computeCounts(this.jobs, this.filters, ctx);
    var lbl = this.ref('lblUnverified');
    lbl.textContent = 'Incluir sin verificar' + (counts.totalUnverified ? ' (' + counts.totalUnverified + ')' : '');
    this.ref('summary').innerHTML =
      '<strong>' + counts.visible + '</strong> oferta' + (counts.visible === 1 ? '' : 's') + ' · <strong>' + counts.studios + '</strong> empresa' + (counts.studios === 1 ? '' : 's') +
      ' · <strong>' + counts.totalUnverified + '</strong> sin verificar' +
      (!this.filters.showUnverified && counts.hiddenUnverified ? ' (<button type="button" class="jp-link" data-action="show-unverified">mostrar ' + counts.hiddenUnverified + ' ocultas</button>)' : (this.filters.showUnverified ? ' (incluidas)' : ''));

    var chips = C.activeFilterChips(this.filters);
    this.ref('chips').innerHTML = chips.length
      ? '<span class="jp-chipcount">' + chips.length + ' filtro' + (chips.length === 1 ? '' : 's') + ' activo' + (chips.length === 1 ? '' : 's') + ':</span>' +
        chips.map(function (c) { return '<span class="jp-appliedchip">' + esc(c.label) + '<button type="button" data-action="clear-chip" data-key="' + c.key + '" aria-label="Quitar filtro ' + esc(c.label) + '">×</button></span>'; }).join('')
      : '';
    this.renderList();
  };

  Panel.prototype.renderList = function () {
    var list = C.applyFilters(this.jobs, this.filters, this.ctx());
    var box = this.ref('list');
    if (!list.length) {
      var why = C.explainEmpty(this.jobs, this.filters, this.ctx()).slice(0, 4);
      var html = '<li class="jp-state jp-empty"><strong>Ninguna oferta coincide</strong>';
      if (C.activeFilterChips(this.filters).length) {
        html += '<p>Causas probables:</p><ul>' + (why.length
          ? why.map(function (w) { return '<li>Quitando «' + esc(w.label) + '» aparecerían ' + w.wouldShow + '.</li>'; }).join('')
          : '<li>La combinación de filtros es demasiado restrictiva.</li>') + '</ul>';
      } else {
        html += '<p>' + (this.jobs.length ? 'No hay ofertas verificadas ahora mismo. Prueba a incluir las ofertas sin verificar.' : 'Todavía no hay ofertas cargadas.') + '</p>';
      }
      html += '<p><button type="button" class="jp-btn" data-action="clear-all">Limpiar filtros</button></p></li>';
      box.innerHTML = html; this.ref('more').innerHTML = '';
    } else {
      var shown = list.slice(0, this.limit), self = this;
      box.innerHTML = shown.map(function (j) { return self.card(j); }).join('');
      this.ref('more').innerHTML = list.length > shown.length
        ? '<button type="button" class="jp-btn" data-action="more">Mostrar más (' + (list.length - shown.length) + ' restantes)</button>' : '';
    }
    this.restoreFocus();
  };

  Panel.prototype.restoreFocus = function () {
    if (!this.refocus) return;
    var n = this.el.querySelector(this.refocus); this.refocus = null;
    if (n) n.focus();
  };

  Panel.prototype.card = function (j) {
    var application=root.VfxApplications&&root.VfxApplications.get(j);
    var saved = !!this.prefs.saved[j.id], disc = !!this.prefs.discarded[j.id];
    var isNew = j.firstSeen && (Date.now() - Date.parse(j.firstSeen)) < 7 * 86400000;
    var wpLabel = L.workplace[j.workplace];
    var eligCls = j.spainEligibility, eligTxt = 'España: ' + L.spainEligibility[j.spainEligibility].toLowerCase();
    var ctTxt = j.contractType === 'freelance' ? 'Freelance/B2B — incompatible' : L.contract[j.contractType];
    var ctCls = j.contractType === 'freelance' ? 'bad' : j.contractType === 'employee' ? 'good' : '';
    var posted = j.postedDate ? 'Publicada: ' + esc(C.formatDate(j.postedDate)) : 'Publicación oficial: no disponible';
    var title = j.safeUrl ? '<a href="' + esc(j.safeUrl) + '" target="_blank" rel="noopener noreferrer">' + esc(j.title) + '</a>' : '<span>' + esc(j.title) + '</span>';
    var tags = [];
    if (j.role !== 'other') tags.push(L.role[j.role]);
    if (j.seniority !== 'unknown') tags.push(L.seniority[j.seniority]);
    j.engines.forEach(function (e) { tags.push(L.engine[e] || e); });
    if (j.companyCategory !== 'unknown') tags.push(L.studioType[j.companyCategory]);

    var warn = '';
    if (!j.directUrl) warn = '<p class="jp-warn">Este enlace lleva a la página de empleo de la empresa, no a la vacante concreta (no se conserva la URL directa).</p>';
    var alt = (j.safeCareersUrl && j.safeCareersUrl !== j.safeUrl)
      ? ' <a class="jp-btn jp-btn-ghost" href="' + esc(j.safeCareersUrl) + '" target="_blank" rel="noopener noreferrer">Página de empleo oficial</a>' : '';
    var evidence = '<details class="jp-why"><summary>Por qué aparece aquí · Ver evidencia</summary><div>' +
      '<p><strong>Puntuación:</strong> ' + j.score + (j.legacy ? ' (sin evaluar)' : '') + '</p>' +
      '<ul>' + j.reasons.map(function (r) { return '<li>' + esc(r) + '</li>'; }).join('') + '</ul>' +
      '<p><strong>Elegibilidad España:</strong> ' + esc(j.spainReason || 'Sin información.') + '</p>' +
      '<p><strong>Contrato:</strong> ' + (j.contractEvidence ? (j.contractType === 'unknown' ? 'ambiguo: la fuente dice «' + esc(j.contractEvidence) + '» (no acredita empleo asalariado)' : 'evidencia «' + esc(j.contractEvidence) + '»') : 'sin evidencia en la fuente (desconocido no es negativo)') + '</p>' +
      '<p><strong>Fuente:</strong> ' + esc(j.sourceLabel) + ' · ' + esc(j.ats) + (j.verified ? ' · verificada' : ' · sin verificar') +
      (j.alsoSeenIn.length ? ' · vista también en ' + esc(j.alsoSeenIn.join(', ')) : '') + '</p>' +
      '<p><strong>Primera detección:</strong> ' + esc(C.timeAgo(j.firstSeen)) + ' · <strong>Última verificación:</strong> ' + esc(C.timeAgo(j.lastSeen)) + '</p>' +
      '</div></details>';

    return '<li class="jp-card' + (disc ? ' disc' : '') + (j.verified ? '' : ' unv') + '" data-job="' + esc(j.id) + '"><article aria-label="' + esc(j.title + ' — ' + j.company) + '">' +
      '<h3 class="jp-card-title">' + title + (isNew ? ' <span class="jp-new">NUEVA</span>' : '') + '</h3>' +
      '<p class="jp-card-sub"><strong>' + esc(j.company) + '</strong> · <span class="jp-src ' + (j.verified ? 'ok' : 'warn') + '">' + esc(j.sourceLabel) + '</span> · ' + posted +
      ' · Detectada ' + esc(C.timeAgo(j.firstSeen)) + '</p>' +
      '<div class="jp-badges">' +
        '<span class="jp-badge wp-' + j.workplace + '">' + esc(wpLabel) + '</span>' +
        (j.location ? '<span class="jp-badge plain">' + esc(j.location) + '</span>' : '') +
        '<span class="jp-badge el-' + eligCls + '" title="' + esc(j.spainReason) + '">' + esc(eligTxt) + '</span>' +
        '<span class="jp-badge ct ' + ctCls + '">' + esc(ctTxt) + '</span>' +
        '<span class="jp-badge plain">' + esc(L.hours[j.hours]) + '</span>' +
      '</div>' +
      (tags.length ? '<div class="jp-tags">' + tags.map(function (t) { return '<span class="jp-tag">' + esc(t) + '</span>'; }).join('') + '</div>' : '') +
      warn + evidence +
      '<div class="jp-actions">' +
        (j.safeUrl ? '<a class="jp-btn jp-btn-primary" href="' + esc(j.safeUrl) + '" target="_blank" rel="noopener noreferrer">' + (j.directUrl ? 'Ver oferta ↗' : 'Ir a la página de empleo ↗') + '</a>' : '<span class="jp-warn">Sin enlace válido</span>') + alt +
        '<button type="button" class="jp-btn" data-action="save" data-id="' + esc(j.id) + '" aria-pressed="' + (saved ? 'true' : 'false') + '">' + (saved ? 'Guardada ✓' : 'Guardar') + '</button>' +
        '<button type="button" class="jp-btn" data-action="'+(application?'application-details':'apply')+'" data-id="'+esc(j.id)+'">'+(application?'Candidatura: '+esc(root.VfxApplications.labels[application.status]||application.status):'He enviado mi candidatura')+'</button>'+
        (disc ? '<button type="button" class="jp-btn" data-action="restore" data-id="' + esc(j.id) + '">Restaurar</button>'
              : '<button type="button" class="jp-btn jp-btn-ghost" data-action="discard" data-id="' + esc(j.id) + '">Descartar</button>') +
      '</div></article></li>';
  };

  // ───────────────────────── Guardadas ─────────────────────────
  Panel.prototype.renderSaved = function () {
    var p = this.pane('saved'); if (!p) return;
    var self = this, ids = Object.keys(this.prefs.saved);
    var byId = {}; this.jobs.forEach(function (j) { byId[j.id] = j; });
    var live = ids.filter(function (i) { return byId[i] && byId[i].status !== 'closed'; });
    var gone = ids.filter(function (i) { return live.indexOf(i) < 0; });
    var h = '<p class="jp-note">Las ofertas guardadas se almacenan <strong>solo en este navegador</strong> (no se sincronizan entre dispositivos).</p>';
    if (!ids.length) h += '<div class="jp-state">Aún no has guardado ninguna oferta. Usa «Guardar» en las tarjetas de <button type="button" class="jp-link" data-action="goto-offers">Ofertas</button>.</div>';
    else {
      h += '<ul class="jp-list" aria-label="Ofertas guardadas">' + live.map(function (i) { return self.card(byId[i]); }).join('') + '</ul>';
      if (gone.length) h += '<h3 class="jp-h3">Ya no están en los datos (' + gone.length + ')</h3><ul class="jp-plain">' + gone.map(function (i) {
        var m = self.prefs.savedMeta[i] || {};
        return '<li>' + esc(m.title || i) + (m.company ? ' — ' + esc(m.company) : '') + ' <button type="button" class="jp-btn jp-btn-ghost" data-action="save" data-id="' + esc(i) + '">Quitar</button></li>';
      }).join('') + '</ul>';
    }
    p.innerHTML = h; this.restoreFocus();
  };

  // ───────────────────────── Empresas ─────────────────────────
  Panel.prototype.renderCompanies = function () {
    var p = this.pane('companies'); if (!p) return;
    var d = this.extra.companies;
    if (!d) { p.innerHTML = '<div class="jp-state">Cargando empresas…</div>'; return; }
    var self = this;
    var statusBy = {}; d.status.forEach(function (s) { if (s.company) statusBy[s.company] = s; });
    var regBy = {}; ((d.registry && d.registry.companies) || []).forEach(function (r) { regBy[r.name] = r; });
    var jobsBy = {}; this.jobs.forEach(function (j) { if (j.status === 'active') { var o = jobsBy[j.company] || (jobsBy[j.company] = { all: 0, ver: 0 }); o.all++; if (j.verified) o.ver++; } });

    var rows = {};
    d.list.forEach(function (c) { rows[c.name] = { name: c.name, careers: c.careersUrl, ats: c.type, monitored: c.enabled !== false, cfg: true }; });
    Object.keys(regBy).forEach(function (n) {
      var r = regBy[n]; var o = rows[n] || (rows[n] = { name: n, monitored: false });
      o.country = r.country; o.official = r.officialUrl; o.careers = o.careers || r.careersUrl; o.ats = o.ats || r.ats;
      o.state = r.state; o.reason = r.reason; o.priority = r.priority; o.spain = r.spainCompat; o.method = r.method; o.reliability = r.reliability; o.checked = r.lastChecked;
      if (r.sharedSource) { o.monitored = true; o.lastOk = r.lastChecked; }
    });
    var arr = Object.keys(rows).map(function (n) {
      var o = rows[n], s = statusBy[n];
      o.conn = o.state || 'pending';
      if (s) { o.conn = s.status === 'ok' ? (s.needsReview ? 'pending' : 'active') : s.status === 'disabled' ? 'pending' : (s.errorKind === 'blocked' ? 'blocked' : 'error'); o.lastOk = s.lastSuccess; o.err = s.error; o.needsReview = s.needsReview; }
      var jc = jobsBy[n] || { all: 0, ver: 0 }; o.jobs = jc.all; o.verJobs = jc.ver;
      return o;
    }).sort(function (a, b) { return b.jobs - a.jobs || a.name.localeCompare(b.name); });

    var qEl = p.querySelector('[data-coq]'), sEl = p.querySelector('[data-cost]'), cEl = p.querySelector('[data-coc]');
    var q = qEl ? qEl.value : '', st = sEl ? sEl.value : 'all', cc = cEl ? cEl.value : 'all';
    var countries = {}; arr.forEach(function (o) { if (o.country) countries[o.country] = 1; });
    var shown = arr.filter(function (o) {
      if (q && (o.name + ' ' + (o.country || '') + ' ' + (o.ats || '')).toLowerCase().indexOf(q.toLowerCase()) < 0) return false;
      if (st === 'with-jobs') return o.jobs > 0;
      if (st !== 'all' && o.conn !== st) return false;
      if (cc !== 'all' && o.country !== cc) return false;
      return true;
    });
    var stLabels = { active: 'Conectada', error: 'Con error', blocked: 'Bloqueada', unsupported: 'No soportada', pending: 'Pendiente' };
    var h = '<p class="jp-note">«Monitorizada» = está en la lista que escanea el scanner; «funciona» = su último escaneo fue correcto; «tiene vacantes» = hay ofertas VFX activas ahora. Son tres cosas distintas.</p>' +
      '<div class="jp-main"><div class="jp-field"><label for="' + this.id('coq') + '">Buscar empresa</label><input id="' + this.id('coq') + '" data-coq type="search" value="' + esc(q) + '"></div>' +
      '<div class="jp-field"><label for="' + this.id('cost') + '">Estado</label><select id="' + this.id('cost') + '" data-cost>' +
        [['all', 'Todos'], ['with-jobs', 'Con vacantes'], ['active', 'Conectadas'], ['error', 'Con error'], ['blocked', 'Bloqueadas'], ['unsupported', 'No soportadas'], ['pending', 'Pendientes']]
          .map(function (o) { return '<option value="' + o[0] + '"' + (o[0] === st ? ' selected' : '') + '>' + o[1] + '</option>'; }).join('') + '</select></div>' +
      '<div class="jp-field"><label for="' + this.id('coc') + '">País</label><select id="' + this.id('coc') + '" data-coc><option value="all">Todos</option>' +
        Object.keys(countries).sort().map(function (c) { return '<option' + (c === cc ? ' selected' : '') + '>' + esc(c) + '</option>'; }).join('') + '</select></div></div>' +
      '<p class="jp-summary" role="status" aria-live="polite"><strong>' + shown.length + '</strong> de ' + arr.length + ' empresas</p>';
    h += shown.length ? '<ul class="jp-colist" aria-label="Empresas">' + shown.map(function (o) {
      return '<li class="jp-co"><div class="jp-co-h"><strong>' + esc(o.name) + '</strong>' + (o.country ? ' <span class="jp-tag">' + esc(o.country) + '</span>' : '') +
        ' <span class="jp-badge conn-' + o.conn + '">' + esc(stLabels[o.conn] || o.conn) + '</span></div>' +
        '<p class="jp-co-m">' + (o.monitored ? 'Monitorizada' : 'No monitorizada') + ' · ' + (o.conn === 'active' ? 'funciona' : 'no confirmada') + ' · ' +
        '<strong>' + o.jobs + '</strong> vacante' + (o.jobs === 1 ? '' : 's') + ' VFX' + (o.jobs ? ' (' + o.verJobs + ' verificadas)' : '') + '</p>' +
        '<p class="jp-co-m">ATS: ' + esc(o.ats || 'desconocido') + (o.method ? ' · método: ' + esc(o.method) : '') + (o.reliability ? ' · fiabilidad: ' + esc(o.reliability) : '') +
        ' · Último éxito: ' + esc(o.lastOk ? C.timeAgo(o.lastOk) : 'nunca') + ' · España: ' + esc(o.spain ? o.spain : 'no confirmado') +
        (o.priority ? ' · prioridad: ' + esc(o.priority) : '') + '</p>' +
        ((o.err || o.reason) ? '<p class="jp-co-m' + (o.err ? ' jp-warn' : '') + '">' + (o.err ? 'Última incidencia: ' + esc(o.err) : 'Nota: ' + esc(o.reason)) + '</p>' : '') +
        '<div class="jp-actions">' + (C.safeUrl(o.careers || o.official) ? '<a class="jp-btn" href="' + esc(C.safeUrl(o.careers || o.official)) + '" target="_blank" rel="noopener noreferrer">Ver fuente ↗</a>' : '') +
        '</div></li>';
    }).join('') + '</ul>' : '<div class="jp-state">Ninguna empresa coincide con ese filtro.</div>';
    var keepFocus = document.activeElement && p.contains(document.activeElement) ? document.activeElement.id : null;
    var caret = qEl && document.activeElement === qEl ? qEl.selectionStart : null;
    p.innerHTML = h;
    if (keepFocus) { var f = document.getElementById(keepFocus); if (f) { f.focus(); if (caret !== null && f.setSelectionRange) try { f.setSelectionRange(caret, caret); } catch (e) { } } }
  };

  // ───────────────────────── Fuentes y scanner (admin) ─────────────────────────
  Panel.prototype.renderSources = function () {
    var p = this.pane('sources'); if (!p) return;
    var d = this.extra.sources;
    if (!d) { p.innerHTML = '<div class="jp-state">Cargando estado del scanner…</div>'; return; }
    var r = d.report, h = '';
    if (!r) h += '<div class="jp-banner">Todavía no existe <code>data/scanner-report.json</code>: se genera en la primera ejecución del scanner V2. Mientras tanto solo se muestra el estado básico.</div>';
    else {
      var s = r.summary || {}, age = (Date.now() - Date.parse(r.generatedAt || '')) / 3600000;
      if (isFinite(age) && age > 13) h += '<div class="jp-banner">El último informe tiene ' + Math.floor(age) + ' h: el scanner debería ejecutarse cada 6 h. Revisa GitHub Actions.</div>';
      h += '<p class="jp-note">Estadísticas calculadas por el scanner el ' + esc(r.generatedAt) + ' (' + esc(C.timeAgo(r.generatedAt)) + ') — no se recalculan en el navegador.</p>' +
        '<div class="jp-stats">' + [
          ['Último escaneo', C.timeAgo(r.generatedAt)], ['Duración', (r.durationSec != null ? r.durationSec + ' s' : '—')],
          ['Fuentes correctas', s.sourcesOk], ['Fuentes con fallo', s.sourcesFailed],
          ['Ofertas oficiales', s.officialJobs], ['Señales de agregador', (s.aggregatorJobs || 0) + (s.signalJobs || 0)],
          ['Peso de agregadores', (s.aggregatorShare != null ? s.aggregatorShare + ' %' : '—')], ['Duplicados fusionados', s.duplicatesMerged],
          ['Sin dato de modalidad', s.unknownWorkplace], ['Sin dato de elegibilidad', s.unknownEligibility], ['Sin dato de contrato', s.unknownContract],
          ['Metadatos completos', (s.metadataComplete != null ? s.metadataComplete + ' %' : '—')]
        ].map(function (x) { return '<div class="jp-stat"><span>' + esc(x[0]) + '</span><strong>' + esc(x[1] == null ? '—' : x[1]) + '</strong></div>'; }).join('') + '</div>';
    }
    h += '<p class="jp-row"><a class="jp-btn" href="' + esc(WORKFLOW_URL) + '" target="_blank" rel="noopener noreferrer">Abrir workflow en GitHub Actions ↗</a> ' +
      '<span class="jp-note">La ejecución manual se hace desde GitHub (botón «Run workflow»); esta página no puede lanzarla.</span></p>';
    var st = d.status || [];
    h += '<h3 class="jp-h3">Estado por fuente</h3><ul class="jp-colist">' + st.map(function (x) {
      var name = x.company || x.source || '—', ok = x.status === 'ok';
      return '<li class="jp-co"><div class="jp-co-h"><strong>' + esc(name) + '</strong> <span class="jp-badge conn-' + (ok ? 'active' : x.status === 'disabled' ? 'pending' : 'error') + '">' + esc(x.status) + '</span>' +
        (x.ats ? ' <span class="jp-tag">' + esc(x.ats) + '</span>' : '') + '</div>' +
        '<p class="jp-co-m">Ofertas: ' + esc(x.jobsFound == null ? '—' : x.jobsFound) + (x.totalPostingsSeen != null ? ' de ' + esc(x.totalPostingsSeen) + ' vistas' : '') +
        (x.durationMs != null ? ' · ' + esc(x.durationMs) + ' ms' : '') + (x.metadataComplete != null ? ' · metadatos ' + esc(x.metadataComplete) + ' %' : '') +
        (x.lastAttempt ? ' · intento ' + esc(C.timeAgo(x.lastAttempt)) : '') + (x.lastSuccess ? ' · último éxito ' + esc(C.timeAgo(x.lastSuccess)) : '') + '</p>' +
        (x.needsReview ? '<p class="jp-co-m jp-warn">0 coincidencias en una fuente poco fiable (HTML): revisar a mano.</p>' : '') +
        (x.incomplete ? '<p class="jp-co-m jp-warn">Resultado incompleto: no se usó para cerrar ofertas.</p>' : '') +
        (x.error ? '<p class="jp-co-m jp-warn">' + esc(x.errorKind ? x.errorKind + ': ' : '') + esc(x.error) + (x.consecutiveFailures ? ' (' + esc(x.consecutiveFailures) + ' fallos seguidos)' : '') + '</p>' : '') + '</li>';
    }).join('') + '</ul>';
    if (r && r.history && r.history.length) {
      h += '<h3 class="jp-h3">Historial reciente</h3><ul class="jp-plain">' + r.history.slice(0, 10).map(function (x) {
        return '<li>' + esc(x.ranAt) + ' — ' + esc(x.activeJobs) + ' activas (' + esc(x.officialJobs) + ' oficiales, ' + esc(x.aggregatorJobs) + ' agregador) · fuentes ok ' + esc(x.sourcesOk) + ' / fallo ' + esc(x.sourcesFailed) + '</li>';
      }).join('') + '</ul>';
    }
    p.innerHTML = h;
  };

  // ───────────────────────── Mis candidaturas / Ajustes ─────────────────────────
  Panel.prototype.renderApps = function () {
    var p = this.pane('apps'); if (!p) return;
    if(root.VfxPrivateAuth&&root.VfxPrivateAuth.user&&p.contains(document.activeElement)&&document.activeElement.matches('input,textarea'))return;
    if(root.VfxApplications)root.VfxApplications.mount(p);
  };

  Panel.prototype.renderSettings = function () {
    var p = this.pane('settings'); if (!p) return;
    var s = this.prefs.settings;
    p.innerHTML = '<p class="jp-note">Preferencias de este navegador. No se envían a ningún servidor.</p>' +
      '<label class="jp-check"><input type="checkbox" data-setting="persistFilters"' + (s.persistFilters ? ' checked' : '') + '> Recordar mis filtros (versión de formato 1)</label>' +
      '<label class="jp-check"><input type="checkbox" data-setting="showDiscarded"' + (s.showDiscarded ? ' checked' : '') + '> Mostrar ofertas descartadas (para poder restaurarlas)</label>' +
      '<div class="jp-actions"><button type="button" class="jp-btn" data-action="clear-saved">Borrar guardadas (' + Object.keys(this.prefs.saved).length + ')</button>' +
      '<button type="button" class="jp-btn" data-action="clear-discarded">Restaurar descartadas (' + Object.keys(this.prefs.discarded).length + ')</button>' +
      '<button type="button" class="jp-btn" data-action="reload">Recargar datos</button></div>';
  };

  // ───────────────────────── API pública ─────────────────────────
  function mount(el, opts) {
    if (!el) return null;
    if (el.__jobsPanel) { el.__jobsPanel.load(!!(opts && opts.reload)); return el.__jobsPanel; }
    var p = new Panel(el, opts); el.__jobsPanel = p; return p;
  }
  root.VfxJobsUI = { mount: mount, panels: panels, _readPrefs: readPrefs };
})(typeof self !== 'undefined' ? self : this);
