# Pruebas

Todo se ejecuta **sin red** y **sin tocar datos de producción**: el scanner usa adaptadores simulados y los tests de
navegador interceptan Firebase y `data/*.json` con los fixtures de `tests/fixtures/`.

| Capa | Qué cubre | Comando |
|------|-----------|---------|
| Python (scanner) | clasificación, ciclo de vida, deduplicación, adaptadores, registro, `run()` completo | `python -m pytest -q tests --ignore=tests/e2e` |
| JavaScript (lógica pura) | modelo de filtros, ordenación, saneado, migración de registros | `node --test "tests/js/*.test.js"` |
| E2E en Chromium | filtros UI-01…UI-12, seguridad del admin, móvil 360 px, accesibilidad (axe-core) | `python -m pytest -q tests/e2e` |

## Preparación (una vez)

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium
npm install            # solo instala axe-core para las pruebas de accesibilidad
```

Si `axe-core` no está instalado, los tests de accesibilidad se **omiten explícitamente** (no pasan en silencio).

## Notas

- `tests/e2e/harness.py` simula Firebase (Auth y Firestore): prueban el **código cliente**, no las reglas reales de
  Firestore (ver `SEGURIDAD_ADMIN.md`).
- Los fixtures de HTML de Mundfish y AXIOM están **reconstruidos** a partir de las páginas oficiales del 2026-10-21;
  no son una captura literal.
- Las fechas del fixture de ofertas se desplazan en cada ejecución para que los tests no dependan del día.
- Capturas opcionales: los tests móviles/escritorio guardan imágenes en `/tmp` (no se versionan).
