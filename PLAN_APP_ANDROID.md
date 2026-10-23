# Plan: llevar el buscador de empleo a una app Flutter (Android primero)

**Idea clave: no hace falta backend.** El scanner de GitHub Actions ya hace todo el trabajo difícil y publica
`data/jobs.json` en GitHub Pages cada 6 h. La app solo tiene que **descargar ese JSON y mostrarlo**. La clasificación
(elegibilidad España, contrato, relevancia explicada, verificada/sin verificar) viaja ya calculada en cada oferta, así que
la web y la app muestran lo mismo sin duplicar lógica de negocio.

```
GitHub Actions (scanner Python) ──► data/jobs.json ──► GitHub Pages (HTTPS público)
                                                          ├──► Web (jobs-core.js + jobs-ui.js)
                                                          └──► App Flutter (mismo JSON)
```

## 1. Contrato de datos (congelado en `schemaVersion: 2`)

URL: `https://yagovfx.github.io/data/jobs.json` (más `scanner-report.json`, `companies-registry.json` opcionales).

| Campo | Tipo / valores | Notas |
|-------|----------------|-------|
| `id`, `company`, `title`, `url`, `location` | string | `url` = ficha de la vacante si `directUrl` es true |
| `status` | `active` \| `stale` \| `closed` | mostrar solo `active`; `stale` = sin verificar; `closed` nunca |
| `verification` / `sourceKind` | `verified`\|`unverified` · `ats`\|`official-site`\|`aggregator`\|`signal` | por defecto mostrar solo `verified` |
| `directUrl` | bool | si es false, avisar: «lleva a la página de empleo, no a la vacante» |
| `workplaceType` | `remote`\|`hybrid`\|`onsite`\|`unknown` | |
| `spainEligibility` + `spainReason` | `confirmed`\|`possible`\|`unknown`\|`restricted`\|`contradiction` | **independiente** del contrato |
| `contractType` + `contractEvidence` | `employee`\|`freelance`\|`temporary`\|`unknown` | `unknown` con evidencia = ambiguo |
| `hours`, `seniority`, `role`, `engines[]` | enums / lista | |
| `compatibility` | `compatible`\|`review`\|`incompatible` | alimenta las vistas «Compatibles» y «Para revisar» |
| `relevance` | `{score:int, reasons:[string]}` | «Por qué aparece aquí» |
| `firstSeen`, `lastSeen`, `postedDate?`, `closedAt?` | ISO-8601 UTC | `postedDate` casi siempre falta: mostrar «no disponible» |
| `companyCareersUrl?`, `alsoSeenIn?` | string / lista | enlace de contraste y duplicados fusionados |

**Regla de oro heredada:** *desconocido no es negativo.* Un campo ausente o con valor inesperado se trata como
`unknown`, nunca como rechazo. Comprueba `schemaVersion` y, si es mayor de lo que entiende la app, avisa en lugar de fallar.

## 2. Qué se reutiliza y qué se reescribe

| Pieza web | En Flutter |
|-----------|-----------|
| `jobs-core.js` (modelo de filtros, `applyFilters`, `toggleSpain`, `sanitizeFilters`, `explainEmpty`) | Portar a `lib/domain/filters.dart` (~150 líneas, funciones puras) |
| `tests/js/jobs-core.test.js` | **Es la especificación**: portar cada caso a `test/filters_test.dart` |
| `tests/fixtures/jobs_fixture.json` | Copiar a `test/fixtures/` y exigir los **mismos conjuntos esperados** (lista por defecto = 6, España = 2…). Es la prueba de paridad |
| `jobs-ui.js` (render) | Reescribir con widgets (la lógica no está ahí) |
| Scanner, clasificación, relevancia | **No se tocan** |

## 3. Arquitectura mínima

Paquetes: `http` (descarga), `shared_preferences` (guardadas/descartadas/filtros), `path_provider` (caché del JSON),
`url_launcher` (abrir la oferta en el navegador externo), `flutter_riverpod` (estado), `workmanager` +
`flutter_local_notifications` (avisos). Sin WebView con contenido remoto.

```
lib/
  data/jobs_repository.dart     # descarga con ETag, caché en disco, lee offline
  domain/job.dart               # Job.fromJson con defaults «unknown»
  domain/filters.dart           # port de jobs-core.js
  state/                        # providers: jobs, filtros, preferencias
  ui/offers_page.dart  detail_page.dart  saved_page.dart  companies_page.dart  settings_page.dart
```

Modelo (esquema, no código final):

```dart
enum Eligibility { confirmed, possible, unknown, restricted, contradiction }
Eligibility _elig(String? v) =>
    Eligibility.values.firstWhere((e) => e.name == v, orElse: () => Eligibility.unknown);

class Job {
  Job.fromJson(Map<String, dynamic> j)
      : id = '${j['id']}',
        title = j['title'] ?? 'Sin título',
        eligibility = _elig(j['spainEligibility'] as String?),
        verified = j['verification'] == 'verified' && j['status'] == 'active',
        // … resto igual: todo lo desconocido cae en «unknown»
        url = _safeHttpUrl(j['url']);
}
String? _safeHttpUrl(Object? u) { // solo http/https, como safeUrl() de la web
  final p = Uri.tryParse('$u'); return (p != null && (p.scheme == 'http' || p.scheme == 'https')) ? '$u' : null;
}
```

## 4. Pantallas (las mismas que la web)

1. **Ofertas**: búsqueda, vistas (Todos/Compatibles/Para revisar/Guardados), `España`, compatibilidad España,
   «Incluir sin verificar», filtros avanzados en *bottom sheet*, chips retirables, estado vacío que explica la causa.
2. **Detalle**: badges (modalidad, España, contrato, jornada), «Por qué aparece aquí» con `reasons`, evidencia literal,
   aviso de enlace no directo, «Abrir oferta», guardar/descartar.
3. **Guardadas**, 4. **Empresas** (monitorizada ≠ funciona ≠ tiene vacantes), 5. **Ajustes**.
«Fuentes y scanner» es una herramienta de administración: se queda en la web.

## 5. Datos, offline y frescura

- Descarga con `If-None-Match` (ETag de GitHub Pages) → si no cambió, usar la caché.
- Offline primero: abrir siempre con la última caché y refrescar en segundo plano.
- Aviso de datos viejos si `lastUpdated` tiene > 13 h (el scanner corre cada 6 h).

## 6. Avisos de ofertas nuevas

`workmanager` (periodicidad mínima de Android ≈ 15 min; usar 6 h) compara los `id` ya vistos con los nuevos y lanza una
notificación local solo para ofertas **`compatible` y `verified`**. Android puede retrasar tareas en segundo plano (Doze):
es «mejor esfuerzo», no una garantía.

## 7. Candidaturas y sincronización (fase opcional)

«Mis candidaturas» **no puede vivir en GitHub Pages** (es público). Si la quieres: **Supabase** (Auth por email/magic link +
Postgres con *Row Level Security*: cada fila `user_id = auth.uid()`), tablas `saved_jobs(user_id, job_id, saved_at)` y
`applications(user_id, job_id, status, notes, updated_at)`. La app seguiría funcionando sin cuenta con datos locales.
Nunca pongas claves de servicio ni claves de Adzuna en la app.

## 8. Seguridad

HTTPS siempre; solo enlaces http/https; abrir en navegador externo; tratar todo texto del JSON como no confiable
(Flutter no interpreta HTML, no uses `flutter_html` sin sanear); sin secretos en el APK.

## 9. Fases (estimación orientativa, no compromiso)

| Fase | Contenido | Esfuerzo |
|------|-----------|---------:|
| 0 | Proyecto, modelo `Job`, descarga + caché, lista simple | 1 día |
| 1 | Filtros portados + **tests de paridad con el fixture**, detalle, estados vacío/error | 3–4 días |
| 2 | Guardadas/descartadas, empresas, ajustes, offline | 2 días |
| 3 | Notificaciones de nuevas compatibles | 1–2 días |
| 4 | Supabase: cuenta, sincronización, candidaturas | 3–5 días |

## 10. Riesgos

- Si cambia `schemaVersion`, la app debe degradar con aviso, no romper.
- `postedDate` y salario no están en los datos: no prometer filtros por ellos.
- La calidad de la elegibilidad depende de lo que digan las fuentes; la app debe seguir mostrando «sin confirmar».
- Estimaciones de esfuerzo: orientativas, sin haber construido la app.
