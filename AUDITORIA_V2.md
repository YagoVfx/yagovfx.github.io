# Auditoría V2 — VFX Job Tracker

Fecha de la auditoría: 2026-10-21 · Alcance: el repositorio recibido (`yagovfx_github_io.zip`) y la especificación
`VFX_Job_Tracker_V2_Especificacion_Claude.md`.

**Método.** Primero se reprodujeron los fallos sobre una copia intacta del código original, en Chromium real
(Playwright), con Firebase simulado y datos de prueba (nunca producción). Después se corrigió la causa raíz y se
repitió la comprobación. Los datos de producción solo se leyeron (copia local de `data/`).

## 0. Lo que NO pude reproducir (importante)

La especificación habla de los botones **«Compatibilidad España»** e **«Incluir sin verificar»**
(`setVfxEligibility`, `setVfxUnverified`). **No existen en este repositorio**: ni en `index.html`, ni en `index_.html`,
ni en el zip anidado (que es de agosto). Los defectos 1 y 2 de la especificación pertenecen, por tanto, a una versión
desplegada que no estaba en el ZIP, y **no puedo afirmar su causa raíz**. Lo que sí hice: implementar esos dos
controles desde cero con un único modelo de filtros y pruebas (UI-03…UI-06), y reproducir el defecto 3 (España), que sí
estaba en el código recibido. Si en el sitio desplegado sigues viendo el fallo tras subir esta versión, es que el
despliegue no coincide con el repo.

El checkout recibido solo difiere de `HEAD` en finales de línea (CRLF); `git diff --ignore-space-at-eol` está vacío.

## 1. Hallazgos confirmados

Severidad: **C**rítica · **A**lta · **M**edia · **B**aja.

| ID | Sev. | Hallazgo | Causa raíz | Evidencia (antes) | Estado |
|----|------|----------|-----------|-------------------|--------|
| F-01 | A | El botón «España» no se puede desactivar | `setVfxLocationFilter(val)` asigna siempre el mismo valor; no hay toggle | 2 clics → sigue activo, 2 filas (esperado: inactivo, 5 filas) | Corregido (`toggleSpain`) |
| F-02 | A | La búsqueda pierde el foco en cada tecla | `renderVfxJobsPublic()` reescribe **todo** el panel con `innerHTML`, incluido el `<input>` | escribir «vfx» deja solo «v» y sin foco | Corregido (controles creados una vez; solo se repinta la lista) |
| F-03 | A | El panel de admin no se actualiza tras haber abierto el overlay público | Un único `vfxJobsRenderTargetId` global compartido por ambas vistas | pulsar «Remote» en admin: 2 → 2 filas (esperado 1); el render iba al overlay oculto | Corregido (un panel por contenedor, estado propio) |
| F-04 | C | XSS por contenido externo | Título/empresa/URL interpolados sin escapar en `innerHTML`; `href="${url}"` admite `javascript:` | `onerror` ejecutado; `<b>` inyectado como HTML; `href="javascript:…"` renderizado | Corregido (`escapeHtml`, `safeUrl` solo http/https, `rel=noopener`) |
| F-05 | C | Login de admin inseguro (ver `SEGURIDAD_ADMIN.md`) | Contraseña `admin123` por defecto, comparada en el navegador y guardada **en claro** en el documento de Firestore que lee cualquier visitante; `window.openAdmin()` salta el gate; `setLang()` → `save()` escribe en Firestore desde cualquier visitante | payload a Firestore con `password: "admin123"`; `openAdmin()` abre el admin sin credenciales | Corregido en cliente; **requiere que publiques `firestore.rules`** |
| F-06 | A | Se cierran ofertas reales cuando falla su fuente | `for jid in existing: if jid not in new → closed` sin mirar si la fuente respondió; además se sobrescribe `lastSeen` | 2K «Senior VFX Artist» cerrada tras «No response from 2k.com/careers»; los 228 cerrados comparten `lastSeen=2026-10-08T05:50:01Z` (la hora del escaneo, no la de última detección) | Corregido (`lifecycle.py`) |
| F-07 | A | Falsa oficialidad: ofertas de Adzuna presentadas como ATS | `upgrade_adzuna_jobs_to_direct_links` reescribía `url` (landing del tablero), `ats` y `viaAggregator=false` sin comprobar que la vacante existiera allí | **29 de las 68 activas** eran Adzuna re-etiquetadas; solo **12** vienen de adaptadores oficiales; Adzuna pesa **56/68 = 82 %** (con señales) | Corregido (`attach_company_careers_links`; migración de registros) |
| F-08 | M | Teamtailor se trataba como API fiable | Faltaba `uses_reliable_api=False` (el test existente `test_needs_review` ya fallaba) | 1 test rojo en el original | Corregido |
| F-09 | M | Frontier (Lever EU) devolvía «ok» con 0 ofertas; Guerrilla forzada a scraper HTML | Lever solo entendía `jobs.lever.co`; `return []` silencioso; `"type":"custom"` explícito anulaba la autodetección | Frontier y Guerrilla: `ok`, 0 ofertas | Corregido (host `api.eu.lever.co`, error explícito, `resolve_ats`) — **pendiente de verificar en vivo** |
| F-10 | M | Adzuna informaba `status: ok` aunque fallaran peticiones o se truncara | Los `break` ante error no se reflejaban en el estado | — | Corregido (`partial`, `truncated`) |
| F-11 | M | Mezcla `Unknown`/`unknown` en `remoteScope`; 52 de 68 ofertas con modalidad desconocida | Valores sin normalizar; límite real de los datos | `remoteScope`: 52 «Unknown» | Normalizado. La falta de datos **no se arregla inventando**: se muestra como desconocido |
| F-12 | M | El workflow no habría commiteado `scanner-report.json` | `git add` con lista fija | — | Corregido |
| F-13 | M | En móvil la cabecera sticky (z-index 100) tapa «← Back» del overlay (85) | Orden de capas | `elementFromPoint` del botón = logo, **también en el original** | Corregido solo para el overlay de empleo. El overlay de **Devlog** tiene el mismo patrón y **no se ha tocado** |
| F-14 | M | Contraste insuficiente (WCAG AA) | `--sub` 4,13:1 (oscuro) y 3,95:1 (claro); texto blanco sobre `--accent` 4,38:1 | axe-core: violaciones `color-contrast` (impacto *serious*) | Corregido dentro del panel y del gate (colores derivados del tema) |
| F-15 | B | `hash()` de Python en el ID de reserva | No determinista entre ejecuciones | — | Corregido (`sha1`) |

## 2. Hallazgos de datos (no son bugs, condicionan el producto)

- De 23 empresas configuradas, solo 3 (CD Projekt, Ubisoft, Massive) producían ofertas el 2026-10-08; 4 daban error
  (Respawn, Blizzard, 2K, Activision); la mayoría eran `custom` (scraper HTML) con 0 resultados, lo que no distingue
  «sin vacantes» de «página con JavaScript».
- El scraper genérico exige slugs con ≥2 guiones, así que **nunca habría detectado** `mundfish.com/careers/vfx-artist`.
- El descubrimiento automático de ATS casa por *slug del nombre*: puede dar falsos positivos (p. ej. «Genius Game →
  `genius`», «Gram Games → `gram`», «SmartRecruiters, Inc.»). Esas candidatas se registran como **pendientes**, no como
  conectadas.

## 3. Pendiente y riesgos (severidad)

| Riesgo | Sev. | Detalle |
|--------|------|---------|
| Reglas de Firestore sin publicar | **C** | Hasta que publiques `firestore.rules`, cualquiera con la configuración pública puede intentar escribir en `portfolio/main`. Solo tú puedes hacerlo (consola Firebase). |
| Contraseña antigua comprometida | **C** | `admin123` y la contraseña que hayas puesto estuvieron publicadas. Cámbiala donde la reutilices. |
| Adaptadores nuevos sin verificación en vivo | A | Mundfish, AXIOM, Lever EU, Larian, Saber ES, Keywords, Scopely, Gameloft: probados con HTTP simulado; el sandbox no tiene red. Mira el informe tras la primera ejecución. |
| `index_.html` público | A | Copia antigua del sitio con la misma contraseña por defecto. Recomendado: `git rm index_.html`. |
| Reglas reales de Firestore y proveedor de Auth | A | No pude comprobar tu proyecto Firebase. |
| Overlay de Devlog tapado en móvil | M | Mismo defecto F-13, fuera de alcance. |
| Fechas oficiales de publicación | M | Solo Adzuna aporta `postedDate`; los adaptadores ATS no lo recogen todavía. |
| Salario | B | Los datos no lo traen; no hay filtro de salario. |
| Compatibilidad con navegadores | B | Probado solo en Chromium. `color-mix()` requiere navegadores de 2023 en adelante. |
