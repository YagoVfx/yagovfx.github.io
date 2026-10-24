/*
 * jobs-core.js — lógica PURA del panel de empleo (sin DOM, sin red).
 * Funciona como <script> clásico (expone window.VfxJobsCore) y como módulo
 * CommonJS en Node (tests con `node --test`).
 *
 * Separación pedida por la especificación §2:
 *   estado (defaultFilters)  →  filtrado (applyFilters, función pura)
 *   →  conteos derivados (computeCounts, explainEmpty)  →  render (jobs-ui.js)
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.VfxJobsCore = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var FILTERS_VERSION = 1;

  var defaultFilters = Object.freeze({
    query: '',
    view: 'all',               // all | compatible | review | saved
    workplace: 'all',          // all | remote | hybrid | onsite | unknown
    location: 'all',           // all | spain | <texto de ubicación exacto>
    spainEligibility: 'all',   // all | confirmed | possible | unknown | restricted
    contract: 'all',           // all | employee | freelance | temporary | unknown
    seniority: 'all',          // all | junior | mid | senior | lead | unknown
    role: 'all',               // all | vfx | tech-vfx | technical-artist | other
    engine: 'all',             // all | unreal | unity | houdini | proprietary
    company: 'all',
    studioType: 'all',         // all | aaa | indie | unknown
    ats: 'all',
    dateRange: 'all',          // all | 7 | 30 | 90
    hours: 'all',              // all | full | part | unknown
    showUnverified: false,
    showPossibleMatches: false,
    sort: 'relevance'          // relevance | recent | company | title | verified
  });

  var ENUMS = {
    view: ['all', 'compatible', 'review', 'saved'],
    workplace: ['all', 'remote', 'hybrid', 'onsite', 'unknown'],
    spainEligibility: ['all', 'confirmed', 'possible', 'unknown', 'restricted'],
    contract: ['all', 'employee', 'freelance', 'temporary', 'unknown'],
    seniority: ['all', 'junior', 'mid', 'senior', 'lead', 'unknown'],
    role: ['all', 'vfx', 'tech-vfx', 'technical-artist', 'other'],
    engine: ['all', 'unreal', 'unity', 'houdini', 'proprietary'],
    studioType: ['all', 'aaa', 'indie', 'unknown'],
    dateRange: ['all', '7', '30', '90'],
    hours: ['all', 'full', 'part', 'unknown'],
    sort: ['relevance', 'recent', 'company', 'title', 'verified']
  };

  var LABELS = {
    workplace: { remote: 'Remoto', hybrid: 'Híbrido', onsite: 'Presencial', unknown: 'Modalidad desconocida' },
    spainEligibility: { confirmed: 'Confirmada', possible: 'Posible', unknown: 'Sin confirmar', restricted: 'Restringida', contradiction: 'Contradicción: revisar' },
    contract: { employee: 'Empleo asalariado', freelance: 'Freelance/B2B', temporary: 'Temporal', unknown: 'Contrato desconocido' },
    seniority: { junior: 'Junior', mid: 'Mid', senior: 'Senior', lead: 'Lead', unknown: 'Nivel desconocido' },
    role: { vfx: 'VFX', 'tech-vfx': 'Technical VFX', 'technical-artist': 'Technical Artist', other: 'Otro rol' },
    hours: { full: 'Jornada completa', part: 'Jornada parcial', unknown: 'Jornada desconocida' },
    studioType: { aaa: 'AAA', indie: 'Indie', unknown: 'Tipo desconocido' },
    sourceKind: { ats: 'ATS oficial', 'official-site': 'Web oficial', aggregator: 'Agregador (señal)', signal: 'Señal sin oferta concreta' },
    view: { all: 'Todos', compatible: 'Compatibles', review: 'Para revisar', saved: 'Guardados' },
    sort: { relevance: 'Más relevantes', recent: 'Más recientes', company: 'Empresa A-Z', title: 'Cargo A-Z', verified: 'Última verificación' },
    dateRange: { '7': 'Últimos 7 días', '30': 'Últimos 30 días', '90': 'Últimos 90 días' },
    engine: { unreal: 'Unreal', unity: 'Unity', houdini: 'Houdini', proprietary: 'Motor propio' }
  };

  var OFFICIAL_ATS = ['greenhouse', 'lever', 'ashby', 'smartrecruiters', 'recruitee', 'personio',
    'teamtailor', 'workday', 'workable', 'massive-wp'];

  // ───────────── seguridad de salida ─────────────
  function escapeHtml(v) {
    return String(v == null ? '' : v).replace(/[&<>"'`]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '`': '&#96;' }[c];
    });
  }
  /** Solo http/https. Cualquier otro esquema (javascript:, data:, vbscript:...) → ''. */
  function safeUrl(u) {
    if (typeof u !== 'string') return '';
    var t = u.trim();
    if (!/^https?:\/\//i.test(t)) return '';
    try { var p = new URL(t); return (p.protocol === 'http:' || p.protocol === 'https:') ? p.href : ''; }
    catch (e) { return ''; }
  }

  // ───────────── normalización / migración de registros ─────────────
  function lc(v, fallback) { return (typeof v === 'string' && v) ? v.toLowerCase() : fallback; }
  function pick(v, allowed, fallback) { v = lc(v, fallback); return allowed.indexOf(v) >= 0 ? v : fallback; }

  /**
   * Convierte cualquier registro (V1 antiguo o V2) en el modelo canónico que
   * usa la UI. NUNCA inventa: lo que no se sabe queda 'unknown'. Un registro
   * antiguo de Adzuna al que el scanner V1 cambió la URL por la landing de la
   * empresa se trata como agregador sin verificar (misma corrección que hace
   * scanner.migrate_legacy_job).
   */
  function normalizeJob(raw) {
    var j = {};
    for (var k in raw) if (Object.prototype.hasOwnProperty.call(raw, k)) j[k] = raw[k];
    j.id = String(j.id || '');
    j.company = String(j.company || 'Empresa desconocida');
    j.title = String(j.title || 'Sin título');
    j.location = String(j.location || '');
    j.status = pick(j.status, ['active', 'stale', 'closed'], 'active');

    var legacyUpgraded = j.id.indexOf('az-') === 0 && j.ats && j.ats !== 'adzuna' && j.ats !== 'adzuna-signal';
    if (legacyUpgraded) {
      j.companyCareersUrl = j.companyCareersUrl || j.url;
      j.companyAts = j.companyAts || j.ats;
      j.ats = 'adzuna'; j.viaAggregator = true; j.urlIsLanding = true;
    }
    if (j.signalOnly || String(j.id).indexOf('sig-') === 0) j.urlIsLanding = true;

    j.workplace = pick(j.workplaceType, ['remote', 'hybrid', 'onsite', 'unknown'], 'unknown');
    j.remoteScope = lc(j.remoteScope, 'unknown');

    var kind = lc(j.sourceKind, '');
    if (!kind) {
      if (j.ats === 'adzuna-signal' || j.signalOnly) kind = 'signal';
      else if (j.ats === 'adzuna' || j.viaAggregator) kind = 'aggregator';
      else if (OFFICIAL_ATS.indexOf(j.ats) >= 0) kind = 'ats';
      else if (j.ats === 'custom') kind = 'official-site';
      else kind = 'aggregator';
    }
    j.sourceKind = kind;
    j.sourceLabel = LABELS.sourceKind[kind] || LABELS.sourceKind.aggregator;
    var verified = lc(j.verification, '');
    if (!verified) verified = ((kind === 'ats' || kind === 'official-site') && safeUrl(j.url) && !j.signalOnly) ? 'verified' : 'unverified';
    // Una oferta «stale» ya no está confirmada por su fuente.
    j.verified = verified === 'verified' && j.status === 'active';

    j.directUrl = (typeof j.directUrl === 'boolean') ? j.directUrl : !j.urlIsLanding;
    j.safeUrl = safeUrl(j.url);
    j.safeCareersUrl = safeUrl(j.companyCareersUrl);

    j.spainEligibility = pick(j.spainEligibility, ['confirmed', 'possible', 'unknown', 'restricted', 'contradiction'], 'unknown');
    j.spainReason = String(j.spainReason || (j.spainEligibility === 'unknown' ? 'La fuente no aclara si se puede trabajar desde España.' : ''));
    j.contractType = pick(j.contractType, ['employee', 'freelance', 'temporary', 'unknown'], 'unknown');
    j.contractEvidence = String(j.contractEvidence || '');
    j.hours = pick(j.hours, ['full', 'part', 'unknown'], 'unknown');
    j.seniority = pick(j.seniority, ['junior', 'mid', 'senior', 'lead', 'unknown'], 'unknown');
    j.role = pick(j.role, ['vfx', 'tech-vfx', 'technical-artist', 'other'], 'other');
    j.engines = Array.isArray(j.engines) ? j.engines.map(String) : [];
    j.companyCategory = pick(j.companyCategory, ['aaa', 'indie'], 'unknown');
    j.matchType = j.matchType === 'possibleMatch' ? 'possibleMatch' : 'exactMatch';

    if (j.compatibility !== 'compatible' && j.compatibility !== 'review' && j.compatibility !== 'incompatible') {
      j.compatibility = deriveCompatibility(j);
    }
    if (j.relevance && typeof j.relevance.score === 'number') {
      j.score = j.relevance.score;
      j.reasons = Array.isArray(j.relevance.reasons) ? j.relevance.reasons.map(String) : [];
    } else {
      j.score = 0;
      j.reasons = ['Registro en formato anterior: sin puntuación. Se evaluará en el próximo escaneo.'];
    }
    j.legacy = !j.relevance;
    j.alsoSeenIn = Array.isArray(j.alsoSeenIn) ? j.alsoSeenIn.map(String) : [];
    j.sortDate = ts(j.postedDate) || ts(j.firstSeen);
    return j;
  }

  function deriveCompatibility(j) {
    if (j.spainEligibility === 'restricted' || j.contractType === 'freelance' || j.hours === 'part') return 'incompatible';
    if ((j.spainEligibility === 'confirmed' || j.spainEligibility === 'possible') && j.contractType !== 'temporary') return 'compatible';
    return 'review';
  }

  function ts(iso) { var t = Date.parse(iso || ''); return isNaN(t) ? 0 : t; }

  function normalizeJobs(list) {
    return (Array.isArray(list) ? list : []).filter(function (r) { return r && typeof r === 'object'; }).map(normalizeJob);
  }

  // ───────────── filtros ─────────────
  function cloneDefaults() { var o = {}; for (var k in defaultFilters) o[k] = defaultFilters[k]; return o; }

  /** Valida un objeto cualquiera (p. ej. leído de localStorage) → filtros completos y seguros. */
  function sanitizeFilters(input) {
    var f = cloneDefaults();
    if (!input || typeof input !== 'object') return f;
    Object.keys(ENUMS).forEach(function (k) {
      if (typeof input[k] === 'string' && ENUMS[k].indexOf(input[k]) >= 0) f[k] = input[k];
    });
    if (typeof input.query === 'string') f.query = input.query.slice(0, 120);
    ['location', 'company', 'ats'].forEach(function (k) {
      if (typeof input[k] === 'string' && input[k].length <= 160) f[k] = input[k];
    });
    f.showUnverified = input.showUnverified === true;
    f.showPossibleMatches = input.showPossibleMatches === true;
    return f;
  }

  function foldText(s) {
    return String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }
  var SPAIN_RE = /espa(n|ñ)a|spain/i;
  var EU_CODES = 'AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE'.split(' ');
  var EU_NAMES = /\b(austria|belgium|belgica|bulgaria|croatia|croacia|cyprus|chipre|czechia|czech republic|republica checa|denmark|dinamarca|estonia|finland|finlandia|france|francia|germany|alemania|greece|grecia|hungary|hungria|ireland|irlanda|italy|italia|latvia|letonia|lithuania|lituania|luxembourg|luxemburgo|malta|netherlands|paises bajos|poland|polonia|portugal|romania|rumania|slovakia|eslovaquia|slovenia|eslovenia|spain|espana|sweden|suecia|european union|union europea|eu)\b/i;
  var EU_CITIES = /\b(barcelona|madrid|valencia|sevilla|seville|bilbao|malaga|zaragoza|tenerife|las palmas|alicante|paris|lyon|bordeaux|montpellier|berlin|hamburg|frankfurt|munich|munchen|cologne|dusseldorf|darmstadt|amsterdam|rotterdam|utrecht|eindhoven|warsaw|warszawa|krakow|krakows|wroclaw|poznan|gdansk|bucharest|bucuresti|cluj|lisbon|lisboa|porto|stockholm|uppsala|malmo|gothenburg|helsinki|espoo|tampere|copenhagen|aarhus|dublin|cork|prague|praha|brno|bratislava|budapest|vienna|wien|graz|brussels|bruxelles|ghent|gent|antwerp|athens|thessaloniki|rome|roma|milan|milano|turin|torino|tallinn|riga|vilnius|kaunas|ljubljana|zagreb|sofia|limassol|nicosia|valletta)\b/i;
  function isEU(j) {
    var code=String(j.countryCode||j.country||'').toUpperCase();
    if(EU_CODES.indexOf(code)>=0)return true;
    if(/^[A-Z]{2}$/.test(code))return false;
    var location=foldText((j.location||'')+' '+(j.country||'')+' '+(j.remoteScope||''));
    if(EU_NAMES.test(location)||String(j.remoteScope||'').toLowerCase()==='eu')return true;
    if(/\b(usa|united states|canada|united kingdom|uk|switzerland|norway|japan|china|india|australia|brazil|mexico|singapore|turkey|serbia|ukraine|georgia)\b/i.test(location))return false;
    return EU_CITIES.test(location);
  }
  function isSpain(j) {
    return SPAIN_RE.test(j.location) || j.remoteScope === 'spain' || j.spainEligibility === 'confirmed';
  }

  function matchesQuery(j, q) {
    if (!q) return true;
    var hay = foldText([j.company, j.title, j.location, j.engines.join(' '), j.seniority, j.role].join(' '));
    return foldText(q).split(/\s+/).filter(Boolean).every(function (t) { return hay.indexOf(t) >= 0; });
  }

  /**
   * ¿La oferta pasa los filtros? `skip` permite ignorar UNA clave (se usa para
   * explicar resultados vacíos y para los conteos de «qué pasaría si quitase X»).
   */
  function passes(j, f, ctx, skip) {
    ctx = ctx || {};
    var saved = ctx.saved || {}, discarded = ctx.discarded || {};
    var now = ctx.now || Date.now();
    var s = function (k) { return skip === k; };

    if (j.status === 'closed') return false;
    if (!s('view') && f.view === 'saved') { if (!saved[j.id]) return false; }
    else {
      if (!s('showUnverified') && !f.showUnverified && !j.verified) return false;
      if (!s('view') && f.view === 'compatible' && j.compatibility !== 'compatible') return false;
      if (!s('view') && f.view === 'review' && j.compatibility !== 'review') return false;
    }
    if (!ctx.showDiscarded && discarded[j.id] && !(f.view === 'saved' && saved[j.id])) return false;
    if (!s('showPossibleMatches') && !f.showPossibleMatches && j.matchType === 'possibleMatch') return false;
    if (!s('workplace') && f.workplace !== 'all' && j.workplace !== f.workplace) return false;
    if (!s('location') && f.location !== 'all') {
      if (f.location === 'spain') { if (!isSpain(j)) return false; }
      else if (f.location === 'eu') { if (!isEU(j)) return false; }
      else if ((j.location || 'Ubicación desconocida') !== f.location) return false;
    }
    if (!s('spainEligibility') && f.spainEligibility !== 'all') {
      var e = j.spainEligibility === 'contradiction' ? 'unknown' : j.spainEligibility;
      if (e !== f.spainEligibility) return false;
    }
    if (!s('contract') && f.contract !== 'all' && j.contractType !== f.contract) return false;
    if (!s('seniority') && f.seniority !== 'all' && j.seniority !== f.seniority) return false;
    if (!s('role') && f.role !== 'all' && j.role !== f.role) return false;
    if (!s('engine') && f.engine !== 'all' && j.engines.indexOf(f.engine) < 0) return false;
    if (!s('company') && f.company !== 'all' && j.company !== f.company) return false;
    if (!s('studioType') && f.studioType !== 'all' && j.companyCategory !== f.studioType) return false;
    if (!s('ats') && f.ats !== 'all' && j.ats !== f.ats) return false;
    if (!s('hours') && f.hours !== 'all' && j.hours !== f.hours) return false;
    if (!s('dateRange') && f.dateRange !== 'all') {
      var days = parseInt(f.dateRange, 10);
      if (!j.sortDate || (now - j.sortDate) > days * 86400000) return false;
    }
    if (!s('query') && !matchesQuery(j, f.query.trim())) return false;
    return true;
  }

  function sortJobs(list, sort) {
    var arr = list.slice();
    var byDateDesc = function (a, b) { return b.sortDate - a.sortDate; };
    var byTitle = function (a, b) { return a.title.localeCompare(b.title); };
    var cmp = {
      relevance: function (a, b) { return (b.score - a.score) || byDateDesc(a, b) || byTitle(a, b); },
      recent: function (a, b) { return byDateDesc(a, b) || (b.score - a.score) || byTitle(a, b); },
      company: function (a, b) { return a.company.localeCompare(b.company) || byTitle(a, b); },
      title: function (a, b) { return byTitle(a, b) || a.company.localeCompare(b.company); },
      verified: function (a, b) { return (ts(b.lastSeen) - ts(a.lastSeen)) || (b.score - a.score); }
    }[sort] || null;
    return cmp ? arr.sort(cmp) : arr;
  }

  /** Función pura: (ofertas normalizadas, filtros, contexto) → lista visible ordenada. */
  function applyFilters(jobs, f, ctx) {
    f = sanitizeFilters(f);
    return sortJobs(jobs.filter(function (j) { return passes(j, f, ctx); }), f.sort);
  }

  // ───────────── conteos derivados ─────────────
  function computeCounts(jobs, f, ctx) {
    f = sanitizeFilters(f);
    var list = jobs.filter(function (j) { return passes(j, f, ctx); });
    var studios = {};
    list.forEach(function (j) { studios[j.company] = 1; });
    var withUnverified = f.showUnverified ? list.length
      : jobs.filter(function (j) { return passes(j, f, ctx, 'showUnverified'); }).length;
    var active = jobs.filter(function (j) { return j.status === 'active'; });
    return {
      visible: list.length,
      studios: Object.keys(studios).length,
      hiddenUnverified: Math.max(0, withUnverified - list.length),
      totalActive: active.length,
      totalVerified: active.filter(function (j) { return j.verified; }).length,
      totalUnverified: jobs.filter(function (j) { return j.status !== 'closed' && !j.verified; }).length
    };
  }

  /** Opciones de un selector con su conteo, calculado sobre los OTROS filtros. */
  function optionCounts(jobs, f, ctx, key, getter) {
    f = sanitizeFilters(f);
    var counts = {};
    jobs.forEach(function (j) {
      if (!passes(j, f, ctx, key)) return;
      var vals = getter(j);
      (Array.isArray(vals) ? vals : [vals]).forEach(function (v) { if (v) counts[v] = (counts[v] || 0) + 1; });
    });
    return counts;
  }

  // ───────────── chips de filtros activos ─────────────
  var CHIP_ORDER = ['query', 'view', 'workplace', 'location', 'spainEligibility', 'contract', 'seniority', 'role',
    'engine', 'company', 'studioType', 'ats', 'dateRange', 'hours', 'showUnverified', 'showPossibleMatches'];

  function chipLabel(key, f) {
    var v = f[key];
    switch (key) {
      case 'query': return 'Búsqueda: «' + v + '»';
      case 'view': return 'Vista: ' + LABELS.view[v];
      case 'workplace': return 'Modalidad: ' + LABELS.workplace[v];
      case 'location': return v === 'spain' ? 'España' : v === 'eu' ? 'Unión Europea' : 'Ubicación: ' + v;
      case 'spainEligibility': return 'España: ' + LABELS.spainEligibility[v].toLowerCase();
      case 'contract': return 'Contrato: ' + LABELS.contract[v];
      case 'seniority': return 'Nivel: ' + LABELS.seniority[v];
      case 'role': return 'Rol: ' + LABELS.role[v];
      case 'engine': return 'Motor: ' + LABELS.engine[v];
      case 'company': return 'Empresa: ' + v;
      case 'studioType': return 'Estudio: ' + LABELS.studioType[v];
      case 'ats': return 'Fuente: ' + v;
      case 'dateRange': return LABELS.dateRange[v];
      case 'hours': return LABELS.hours[v];
      case 'showUnverified': return 'Incluye sin verificar';
      case 'showPossibleMatches': return 'Incluye coincidencias posibles';
    }
    return key;
  }

  /** Chips retirables. `view: all` y `sort` no cuentan como filtro activo. */
  function activeFilterChips(f) {
    f = sanitizeFilters(f);
    return CHIP_ORDER.filter(function (k) { return f[k] !== defaultFilters[k]; })
      .map(function (k) { return { key: k, label: chipLabel(k, f) }; });
  }

  function clearFilter(f, key) {
    var n = sanitizeFilters(f);
    n[key] = defaultFilters[key];
    return n;
  }

  /** España: 1er clic activa 'spain', 2º clic vuelve a 'all' (defecto #3). */
  function toggleSpain(f) {
    var n = sanitizeFilters(f);
    n.location = n.location === 'spain' ? 'all' : 'spain';
    return n;
  }

  /** Cuando no hay resultados: qué filtro, quitado por sí solo, devolvería ofertas. */
  function explainEmpty(jobs, f, ctx) {
    f = sanitizeFilters(f);
    var out = [];
    CHIP_ORDER.forEach(function (k) {
      if (f[k] === defaultFilters[k]) return;
      var n = jobs.filter(function (j) { return passes(j, f, ctx, k); }).length;
      if (n > 0) out.push({ key: k, label: chipLabel(k, f), wouldShow: n });
    });
    return out.sort(function (a, b) { return b.wouldShow - a.wouldShow; });
  }

  // ───────────── formato ─────────────
  function timeAgo(iso, now) {
    var t = ts(iso); if (!t) return 'desconocido';
    var diff = (now || Date.now()) - t; if (diff < 0) diff = 0;
    var h = Math.floor(diff / 3600000);
    if (h < 1) return 'hace menos de 1 h';
    if (h < 24) return 'hace ' + h + ' h';
    var d = Math.floor(h / 24);
    return 'hace ' + d + (d === 1 ? ' día' : ' días');
  }
  function formatDate(iso) {
    var t = ts(iso); if (!t) return '';
    return new Date(t).toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  }

  return {
    FILTERS_VERSION: FILTERS_VERSION, defaultFilters: defaultFilters, ENUMS: ENUMS, LABELS: LABELS, CHIP_ORDER: CHIP_ORDER,
    escapeHtml: escapeHtml, safeUrl: safeUrl, normalizeJob: normalizeJob, normalizeJobs: normalizeJobs,
    deriveCompatibility: deriveCompatibility, sanitizeFilters: sanitizeFilters, applyFilters: applyFilters,
    passes: passes, sortJobs: sortJobs, computeCounts: computeCounts, optionCounts: optionCounts,
    activeFilterChips: activeFilterChips, clearFilter: clearFilter, toggleSpain: toggleSpain,
    explainEmpty: explainEmpty, timeAgo: timeAgo, formatDate: formatDate, isSpain: isSpain, isEU: isEU, chipLabel: chipLabel
  };
});
