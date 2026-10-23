# Changelog V2

## Seguridad (ver `SEGURIDAD_ADMIN.md`)
- `index.html`: login con Firebase Authentication (email + contraseña); sin contraseña en el código, el estado local ni
  Firestore; `openAdmin` deja de ser global; los visitantes no escriben en Firestore; limpieza automática del documento
  heredado; gate accesible con bloqueo local tras 5 fallos; «Cerrar sesión» en Ajustes.
- Nuevo `firestore.rules` (lectura pública, escritura solo del admin verificado). **Debes publicarlo tú.**

## Panel de empleo (nuevo módulo, sustituye al bloque antiguo de `index.html`)
- `assets/jobs/jobs-core.js` — lógica pura y testeable: modelo único de filtros, `applyFilters`, `toggleSpain`,
  `sanitizeFilters`, `explainEmpty`, migración de registros antiguos, `escapeHtml`/`safeUrl`.
- `assets/jobs/jobs-ui.js` — UI con DOM estable y listeners delegados; un panel por contenedor.
- `assets/jobs/jobs.css` — estilos propios, responsive, contraste AA derivado del tema.
- Pestañas: Ofertas · Guardadas · Empresas · (admin) Mis candidaturas (diseñada, desactivada a propósito) · (admin) Fuentes y
  scanner · Ajustes. Vistas Todos/Compatibles/Para revisar/Guardados; chips; «por qué aparece aquí» con evidencia;
  guardar/descartar/restaurar en el navegador; filtros recordados (versionados).
- Por defecto solo se muestran ofertas **verificadas**; las demás, con «Incluir sin verificar».
- Arreglos: F-01 España no se desactivaba · F-02 la búsqueda perdía el foco · F-03 render compartido admin/overlay ·
  F-04 XSS · F-13 «← Back» tapado en móvil.

## Scanner (`scanner/`)
- Nuevo `classify.py`: elegibilidad España (confirmada/posible/desconocida/restringida/contradicción), contrato, jornada,
  seniority, rol, motor y relevancia **con motivos**. Desconocido ≠ negativo; un agregador nunca «confirma».
- Nuevo `lifecycle.py`: una oferta solo se cierra tras un escaneo **correcto y completo de su fuente**; fallos → `stale`;
  `lastSeen` no se sobrescribe; `closedAt`; poda a los 30 días; Adzuna nunca cierra ofertas de un ATS.
- `scanner.py` reescrito en funciones inyectables: migración de registros antiguos, fusión oficial↔Adzuna (`alsoSeenIn`),
  métricas por fuente, `data/scanner-report.json` (historial de 20 ejecuciones), `schemaVersion: 2`.
- `attach_company_careers_links` sustituye al «upgrade» a enlace directo (F-07).
- `adapters/official_sites.py`: Mundfish y AXIOM VFX. `adapters/lever.py`: host EU y error explícito.
  `adapters/greenhouse.py`: error explícito. `adapters/teamtailor.py`: marcado como poco fiable.
  `sources/adzuna.py`: `partial`/`truncated`. `companies.py`: detección de Mundfish/AXIOM.
  `normalizer.py`: ID de reserva determinista. `scanner/build_registry.py`: genera el registro.
- `data/companies.json`: +7 empresas (Mundfish, AXIOM VFX, Larian, Saber Interactive Spain, Keywords Studios, Scopely,
  Gameloft). `data/companies-registry.json`: 71 empresas con procedencia.

## Infraestructura
- `.github/workflows/vfx-jobs-scanner.yml`: gate de tests antes de escanear; commitea también `scanner-report.json`.
- `.github/workflows/tests.yml` (nuevo): unit + E2E en cada push/PR. `.gitignore`, `package.json`, `package-lock.json`,
  `requirements-dev.txt` (solo para pruebas).

## Pruebas
- Python 162 · JS 21 · E2E en navegador (ver `TEST_REPORT_V2.md` para cifras finales).
- `tests/test_upgrade_adzuna.py` se **reescribió**: su expectativa antigua (cambiar `url`/`ats`/`viaAggregator`) era el defecto F-07.

## Documentos
`AUDITORIA_V2.md` · `SEGURIDAD_ADMIN.md` · `EMPRESAS_Y_FUENTES.md` · `PLAN_APP_ANDROID.md` (plan Flutter) · `TEST_REPORT_V2.md`.

## Compatibilidad
Se conservan: portfolio, devlog, importador, sección «Config» de empresas (`vfxjobs`), diagnóstico del scanner,
`data/jobs.json`/`scanner-status.json` (campos antiguos intactos; los nuevos son aditivos). Los registros antiguos se
migran solos en la primera ejecución y la web los entiende mientras tanto (aviso de «formato anterior»).
