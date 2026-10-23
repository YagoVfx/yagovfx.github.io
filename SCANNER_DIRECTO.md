# Catálogo de portales directos

Desde el 23 de octubre de 2026, `scanner.run()` usa por defecto `sourcePolicy: direct-only`.
No consulta Adzuna ni ejecuta el descubrimiento de ATS basado en agregadores. El workflow
ya no necesita sus claves. El modo mixto se conserva únicamente como opción explícita de
la función Python para compatibilidad y pruebas; el workflow nunca lo activa.

Los registros históricos `az-*`, `sig-*`, `viaAggregator`, `signalOnly` y fuentes de
agregador se excluyen del JSON de ofertas. No se convierten en ofertas oficiales ni se
declaran cerrados por dejar de consultar la fuente. Siguen en el historial de Git.

## Resultado real del primer escaneo

- 30 empresas configuradas; 29 consultas sin excepción y una fallida (Respawn, URL 404).
- 33 ofertas activas de fuentes directas: 29 ATS y 4 webs oficiales.
- Una oferta directa antigua pendiente de verificar (`stale`); 19 cerradas conservadas como historial.
- 317 registros antiguos de agregadores excluidos; cero ofertas de Adzuna en el catálogo.

Consulta los resultados vigentes en `data/scanner-report.json` y `data/scanner-status.json`.
Una respuesta HTTP correcta no demuestra que el scraper funcione: los HTML con cero
coincidencias siguen marcados como `needsReview`.

## Conexiones reparadas y verificadas en vivo

| Empresa | Conexión | Ofertas activas detectadas |
|---|---|---:|
| Lighthouse Games | Workable, cuenta `lighthousegames` | 3 |
| Rebellion | Workable, cuenta `rebellion` | 2 |
| Jagex | Workable, cuenta `jagex-limited` | 0 |
| Side/PTW | Workable, cuenta `sideinc` | 4 |
| Embark | Teamtailor, listado `/jobs` completo | 1 |
| Sumo Digital | Página oficial `/careers/` | 1 |
| Blizzard | Workday, nuevo tenant `xboxgaming` | 2 |
| Activision | Workday, nuevo tenant `xboxgaming` | 4 |

El antiguo portal global Workable ignoraba `companyIds` y devolvía anuncios de cualquier
empresa. Ahora se rechaza esa vía y se exige una URL de cuenta verificada. Las ofertas
duplicadas por ubicación se fusionan conservando las ubicaciones y la fecha publicada.

## Qué publicar

Sube desde GitHub Desktop los cambios de scanner, workflow, datos, assets y tests.
El JSON regenerado contiene la política y las ofertas directas. La web lo aplica al cargar.
La APK 0.2.0 excluye agregadores incluso antes de actualizar el JSON remoto; para recibir
las 33 ofertas nuevas debes publicar los JSON y actualizar desde la app.

No hay cambios desplegados automáticamente por este trabajo. Los builds de la app están
ignorados en Git; instala `mobile/dist/yago-vfx-jobs-0.2.0.apk` sobre la primera versión.

## Pendientes

Respawn sigue fallando; Epic, Build A Rocket Boy, Room8, 2K y otros scrapers sin resultados
necesitan conectores específicos o un portal de empleo confirmado. Que haya una empresa
en el registro no implica que esté conectada ni que existan vacantes para trabajar desde España.
Los documentos de auditoría anteriores describen la situación previa a este cambio.
