# Informe de pruebas V2

Fecha: 2026-10-22 · Entorno: Chromium (Playwright 1.56, `chromium-1194`) · Node 22.22 · Python 3.12 · axe-core 4.14.0 ·
**sin acceso a internet** (el sandbox no resuelve DNS) · Firebase **simulado** · datos de prueba, nunca producción.

## Resultado global

| Suite | Pruebas | Resultado |
|-------|--------:|-----------|
| Python (scanner, clasificación, ciclo de vida, adaptadores, registro) | 162 | 162 ✔ |
| JavaScript (lógica pura del panel, `node --test`) | 21 | 21 ✔ |
| E2E en navegador real (filtros, seguridad admin, móvil, accesibilidad, regresión) | 72 | 72 ✔ |
| **Total** | **255** | **255 ✔ · 0 omitidas · 0 fallos** |

Línea base del código recibido: 72 pasaban y **1 fallaba** (`test_needs_review`, Teamtailor), que era un bug real, ya corregido.

## Antes / después (mismo escenario, mismo arnés)

| Caso | Código original | Código V2 |
|------|-----------------|-----------|
| «España» pulsado 2 veces | sigue activo, 2 filas | desactiva, vuelve a la lista completa (`test_ui01_ui02…`) |
| Escribir «vfx» en la búsqueda | queda «v», sin foco | texto completo, foco y cursor conservados (`test_ui08…`) |
| Filtro en admin tras usar el overlay | 2 → 2 filas (no se actualiza) | independientes (`test_ui10…`) |
| Título con `<img onerror>` / URL `javascript:` | **XSS ejecutado**, enlace `javascript:` | texto literal, sin enlace (`test_untrusted_content…`) |
| Contraseña en el payload a Firestore | `"password":"admin123"` | ausente (`test_authenticated_save…`) |
| `window.openAdmin()` | abre el admin sin credenciales | no existe en `window` (`test_openAdmin_is_not_a_global…`) |
| Cambiar idioma como visitante | escribe en Firestore | 0 escrituras (`test_visitor_actions_never_write…`) |
| Scanner con fuentes caídas | Según el código y los datos reales de producción cierra las ofertas de empresas con error (p. ej. 2K «Senior VFX Artist»); **no se ejecutó el original** en este caso | Ejecutado el scanner real sobre una copia de los datos con las 30 fuentes caídas: **0 cerradas**; 68 pasan a `stale` por llevar >14 días sin verificarse; `lastSeen` intacto |
| «← Back» del overlay en móvil | tapado por la cabecera | clicable y cierra (`test_mobile_back_button…`) |
| Contraste (axe) | 4,13:1 y 4,38:1 | 0 violaciones, tema oscuro y uno claro |

**Comprobación de que los tests detectan los fallos (mutación).** Reintroduje a propósito el bug original en tres sitios y
los tests fallaron: cerrar ofertas siempre (7 tests rojos), que un agregador confirme elegibilidad (1) y que «España» no
alterne (1). Al restaurar, todo volvió a verde.

## Qué se probó de verdad

**Filtros y UI en Chromium** (`tests/e2e/test_jobs_ui.py`): UI-01…UI-10 de la especificación y UI-12 (teclado: todos los
controles alcanzables con Tab y accionables con Enter/Espacio/flechas); vistas rápidas; chips retirables; estado vacío con
causa y «Limpiar filtros»; ordenación; búsqueda sin acentos/mayúsculas; filtros avanzados con conteos; tarjeta con
procedencia, desconocidos y evidencia; ranking; registros heredados; guardar/descartar/restaurar y persistencia tras recarga;
preferencias corruptas; pestañas con navegación por teclado y ARIA; Empresas; Fuentes y scanner (admin) con y sin informe;
error de carga con reintento; dataset vacío; aviso de datos viejos y de formato anterior.

**Seguridad del admin** (`test_admin_security.py`, 17 pruebas): sin contraseña en el código/estado/payloads; credenciales
vacías, incorrectas y de email desconocido (mismo mensaje); contraseña antigua rechazada; bloqueo tras 5 fallos; login;
cierre y pérdida de sesión; visitantes sin escrituras; limpieza del documento heredado; el panel no se monta sin sesión.

**Móvil 360 px, accesibilidad y regresión**: sin scroll horizontal, objetivos táctiles, `axe-core` WCAG 2.1 A/AA sobre
4 pestañas públicas, panel admin (fuentes y vacío) y el gate; funciones previas: portfolio, idioma, botón público de
empleo (con clic real), las 17 secciones del admin (todas las que existen en `index.html`), gestor de empresas, diagnóstico del scanner (con datos hostiles y sin
fichero) y compatibilidad con un `jobs.json` antiguo.

**Scanner**: clasificación (DATA-03/04/05), ciclo de vida (DATA-01/02), `run()` de extremo a extremo con adaptadores
simulados, migración de registros reales, deduplicación, URL de la vacante nunca sustituida por una landing (DATA-06),
resolución de ATS (`custom` ya no anula un ATS conocido, Lever EU), adaptadores de Mundfish y AXIOM, ID determinista,
validación de `companies.json` y del registro. Además se **ejecutó el scanner real como script** sobre una copia de los
datos de producción (ver tabla).

## Qué NO se probó (sé que falta)

- **Ninguna fuente en vivo.** No hay red: Mundfish, AXIOM, Lever EU, Larian, Saber ES, Keywords, Scopely y Gameloft se
  probaron con HTTP simulado y con HTML **reconstruido** de las páginas oficiales. Pueden fallar al primer escaneo real.
- **Firebase real**: ni Auth, ni reglas de Firestore, ni tu proyecto. El cliente se probó contra un simulador.
- **Los workflows de GitHub Actions** no se ejecutaron (solo se validó su lógica y que los comandos existen).
- Otros navegadores (Firefox, Safari), dispositivos móviles reales (se emuló un viewport de 360 px), lectores de pantalla
  (solo axe automático) y el cambio de tema real desde la interfaz (el tema claro se comprobó fijando las variables CSS).
- Pruebas visuales de regresión, carga con miles de ofertas y la app Flutter (solo hay plan).
- El overlay de **Devlog** sigue con el defecto de capas en móvil (fuera de alcance).

## Cómo reproducirlo

```bash
pip install -r requirements-dev.txt && python -m playwright install chromium && npm install
python -m pytest -q tests --ignore=tests/e2e
node --test "tests/js/*.test.js"
python -m pytest -q tests/e2e
```
