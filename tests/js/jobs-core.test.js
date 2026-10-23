// Ejecutar: node --test tests/js/
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const C = require('../../assets/jobs/jobs-core.js');

const raw = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'fixtures', 'jobs_fixture.json'), 'utf8')).jobs;
const NOW = Date.parse('2026-10-20T00:00:00Z');
const jobs = C.normalizeJobs(raw);
const ctx = (o) => Object.assign({ now: NOW, saved: {}, discarded: {} }, o || {});
const F = (o) => Object.assign({}, C.defaultFilters, o || {});
const ids = (list) => list.map((j) => j.id).sort();

test('por defecto solo se ven ofertas verificadas y activas (sin cerradas ni agregador)', () => {
  assert.deepEqual(ids(C.applyFilters(jobs, F(), ctx())), ['gh-1', 'gh-2', 'gh-3', 'gh-4', 'gh-5', 'sr-legacy']);
});

// UI-01 / UI-02
test('España: 1er toggle filtra, 2º vuelve a todas las ubicaciones', () => {
  let f = F({ showUnverified: true });
  const all = C.applyFilters(jobs, f, ctx()).length;
  f = C.toggleSpain(f);
  assert.equal(f.location, 'spain');
  const es = ids(C.applyFilters(jobs, f, ctx()));
  assert.deepEqual(es, ['az-1', 'az-up', 'gh-1', 'gh-5']);
  f = C.toggleSpain(f);
  assert.equal(f.location, 'all');
  assert.equal(C.applyFilters(jobs, f, ctx()).length, all);
});

// UI-03 / UI-04
test('elegibilidad: una sola opción activa y la lista cambia de forma consistente', () => {
  const base = F({ showUnverified: true });
  const by = (e) => ids(C.applyFilters(jobs, Object.assign({}, base, { spainEligibility: e }), ctx()));
  assert.deepEqual(by('confirmed'), ['gh-1']);
  assert.deepEqual(by('possible'), ['gh-2', 'gh-4']);
  // «contradicción» se agrupa con «sin confirmar»: va a revisión, nunca a confirmada
  assert.deepEqual(by('unknown'), ['az-1', 'az-3', 'az-up', 'gh-5', 'sr-legacy']);
  assert.deepEqual(by('restricted'), ['gh-3']);
  const all = [].concat(by('confirmed'), by('possible'), by('unknown'), by('restricted'));
  assert.equal(new Set(all).size, all.length, 'los grupos no se solapan');
});

// UI-05 / UI-06 con registros unverified
test('«Incluir sin verificar» añade registros agregador y al desmarcar los retira', () => {
  const off = C.applyFilters(jobs, F(), ctx());
  const on = C.applyFilters(jobs, F({ showUnverified: true }), ctx());
  assert.ok(on.length > off.length);
  assert.ok(on.some((j) => !j.verified) && off.every((j) => j.verified));
  const back = C.applyFilters(jobs, F({ showUnverified: false }), ctx());
  assert.deepEqual(ids(back), ids(off));
});

test('«Coincidencias posibles» añade possibleMatch y al desmarcar los retira', () => {
  const base = F({ showUnverified: true });
  const off = C.applyFilters(jobs, base, ctx());
  const on = C.applyFilters(jobs, Object.assign({}, base, { showPossibleMatches: true }), ctx());
  assert.deepEqual(ids(on).filter((i) => !ids(off).includes(i)), ['az-2']);
});

// UI-07
test('cambiar el orden conserva el filtro y solo cambia el orden', () => {
  const f1 = F({ showUnverified: true, workplace: 'remote' });
  const a = C.applyFilters(jobs, Object.assign({}, f1, { sort: 'relevance' }), ctx());
  const b = C.applyFilters(jobs, Object.assign({}, f1, { sort: 'company' }), ctx());
  assert.deepEqual(ids(a), ids(b));
  assert.deepEqual(b.map((j) => j.company), b.map((j) => j.company).slice().sort((x, y) => x.localeCompare(y)));
});

test('búsqueda por varias palabras (AND), sin distinguir mayúsculas ni acentos', () => {
  const f = F({ showUnverified: true, query: 'ALPHA senior' });
  assert.deepEqual(ids(C.applyFilters(jobs, f, ctx())), ['gh-1']);
  assert.deepEqual(ids(C.applyFilters(jobs, F({ showUnverified: true, query: 'barcelóna' }), ctx())), ['az-1', 'az-up']);
  assert.deepEqual(ids(C.applyFilters(jobs, F({ showUnverified: true, query: 'madrid' }), ctx())), ['gh-1']);
});

// UI-09
test('filtros incompatibles → vacío; explainEmpty indica qué filtro devolvería ofertas', () => {
  const f = F({ workplace: 'onsite', spainEligibility: 'confirmed', location: 'spain' });
  assert.equal(C.applyFilters(jobs, f, ctx()).length, 0);
  const why = C.explainEmpty(jobs, f, ctx());
  assert.ok(why.length >= 1 && why.every((w) => w.wouldShow > 0));
  let g = f;
  C.activeFilterChips(f).forEach((c) => { g = C.clearFilter(g, c.key); });
  assert.deepEqual(g, C.sanitizeFilters(C.defaultFilters));
});

test('chips: solo filtros activos; view=all y sort no cuentan', () => {
  assert.deepEqual(C.activeFilterChips(F()), []);
  const chips = C.activeFilterChips(F({ location: 'spain', workplace: 'remote', sort: 'recent', showUnverified: true }));
  assert.deepEqual(chips.map((c) => c.key), ['workplace', 'location', 'showUnverified']);
  assert.ok(chips.find((c) => c.key === 'location').label === 'España');
});

test('contadores derivados: ocultas sin verificar y totales', () => {
  const c = C.computeCounts(jobs, F(), ctx());
  assert.equal(c.visible, 6);
  assert.equal(c.hiddenUnverified, 3);          // az-1, az-3 y az-up (az-2 es possibleMatch)
  assert.equal(c.totalActive, 10);
  const on = C.computeCounts(jobs, F({ showUnverified: true }), ctx());
  assert.equal(on.hiddenUnverified, 0);
});

test('vistas: compatibles / para revisar / guardados', () => {
  const base = F({ showUnverified: true, showPossibleMatches: true });
  const view = (v) => ids(C.applyFilters(jobs, Object.assign({}, base, { view: v }), ctx()));
  assert.deepEqual(view('compatible'), ['gh-1', 'gh-2']);
  assert.deepEqual(view('review'), ['az-1', 'az-2', 'az-3', 'az-up', 'gh-5', 'sr-legacy']);
  // restringidas y freelance solo aparecen en «Todos», marcadas, nunca se pierden en silencio
  assert.ok(view('all').includes('gh-3') && view('all').includes('gh-4'));
  assert.ok(!view('compatible').includes('gh-3') && !view('review').includes('gh-4'));
  const saved = C.applyFilters(jobs, F({ view: 'saved' }), ctx({ saved: { 'az-1': true } }));
  assert.deepEqual(ids(saved), ['az-1']);   // guardadas se ven aunque estén sin verificar
});

test('descartadas se ocultan y se pueden restaurar', () => {
  const d = { 'gh-1': true };
  assert.ok(!ids(C.applyFilters(jobs, F(), ctx({ discarded: d }))).includes('gh-1'));
  assert.ok(ids(C.applyFilters(jobs, F(), ctx({ discarded: d, showDiscarded: true }))).includes('gh-1'));
});

// Seguridad
test('safeUrl solo admite http/https', () => {
  assert.equal(C.safeUrl('javascript:alert(1)'), '');
  assert.equal(C.safeUrl('data:text/html,<script>'), '');
  assert.equal(C.safeUrl(' JaVaScRiPt:alert(1)'), '');
  assert.equal(C.safeUrl('//evil.test'), '');
  assert.equal(C.safeUrl('https://ok.test/a?b=1'), 'https://ok.test/a?b=1');
  assert.equal(C.safeUrl(null), '');
});

test('escapeHtml neutraliza etiquetas y comillas', () => {
  const s = C.escapeHtml('<img src=x onerror="a()"> \'q\' & `b`');
  assert.ok(!/[<>"'`]/.test(s) && s.includes('&amp;'));
});

test('el registro con XSS se normaliza sin ejecutar nada: URL insegura queda vacía', () => {
  const x = jobs.find((j) => j.id === 'az-3');
  assert.equal(x.safeUrl, '');
});

test('sanitizeFilters descarta valores fuera del conjunto permitido', () => {
  const f = C.sanitizeFilters({ workplace: 'hacked', sort: '<script>', location: 'spain', showUnverified: 'yes', query: 'x'.repeat(500), junk: 1 });
  assert.equal(f.workplace, 'all'); assert.equal(f.sort, 'relevance'); assert.equal(f.location, 'spain');
  assert.equal(f.showUnverified, false); assert.equal(f.query.length, 120); assert.ok(!('junk' in f));
  assert.deepEqual(C.sanitizeFilters(null), C.sanitizeFilters(undefined));
});

// Migración / semántica de datos
test('registro antiguo de Adzuna «mejorado» a ATS se trata como agregador sin verificar', () => {
  const legacy = C.normalizeJob({ id: 'az-1', company: 'Scopely', title: 'VFX', ats: 'greenhouse', viaAggregator: false,
    url: 'https://job-boards.greenhouse.io/scopely', status: 'active' });
  assert.equal(legacy.sourceKind, 'aggregator');
  assert.equal(legacy.verified, false);
  assert.equal(legacy.directUrl, false);
  assert.equal(legacy.safeCareersUrl, 'https://job-boards.greenhouse.io/scopely');
});

test('desconocido no se convierte en negativo: valores por defecto «unknown» y compatibilidad «review»', () => {
  const j = C.normalizeJob({ id: 'gh-9', company: 'X', title: 'Senior VFX Artist', ats: 'greenhouse', url: 'https://x.test/1' });
  assert.equal(j.spainEligibility, 'unknown'); assert.equal(j.contractType, 'unknown');
  assert.equal(j.compatibility, 'review'); assert.equal(j.verified, true); assert.equal(j.legacy, true);
});

test('stale nunca cuenta como verificada; closed nunca se muestra', () => {
  const stale = C.normalizeJob({ id: 'gh-1', company: 'X', title: 'VFX', ats: 'greenhouse', url: 'https://x.test', status: 'stale' });
  assert.equal(stale.verified, false);
  assert.ok(!C.applyFilters([stale], F({ showUnverified: false }), ctx()).length);
  assert.ok(C.applyFilters([stale], F({ showUnverified: true }), ctx()).length);
  const closed = C.normalizeJob({ id: 'gh-2', company: 'X', title: 'VFX', ats: 'greenhouse', url: 'https://x.test', status: 'closed' });
  assert.equal(C.applyFilters([closed], F({ showUnverified: true }), ctx()).length, 0);
});

test('ranking: usa la puntuación del scanner y desempata por fecha', () => {
  const a = C.normalizeJob({ id: 'a', company: 'A', title: 'VFX', ats: 'greenhouse', url: 'https://a.test', firstSeen: '2026-10-01T00:00:00Z', relevance: { score: 50, reasons: ['x'] } });
  const b = C.normalizeJob({ id: 'b', company: 'B', title: 'VFX', ats: 'greenhouse', url: 'https://b.test', firstSeen: '2026-10-10T00:00:00Z', relevance: { score: 50, reasons: ['x'] } });
  const c = C.normalizeJob({ id: 'c', company: 'C', title: 'VFX', ats: 'greenhouse', url: 'https://c.test', firstSeen: '2026-10-20T00:00:00Z', relevance: { score: 10, reasons: ['x'] } });
  assert.deepEqual(C.applyFilters([a, b, c], F(), ctx()).map((j) => j.id), ['b', 'a', 'c']);
});

test('timeAgo y formatDate', () => {
  assert.equal(C.timeAgo('2026-10-19T12:00:00Z', NOW), 'hace 12 h');
  assert.equal(C.timeAgo('2026-10-18T00:00:00Z', NOW), 'hace 2 días');
  assert.equal(C.timeAgo('', NOW), 'desconocido');
});
