# Empresas y fuentes

> Actualización del 23-10-2026: la integración se ha ampliado a 70 fuentes configuradas y
> comprobadas en vivo, con 65 ofertas activas oficiales. La última ampliación incorpora
> Highdive, MobilityWare, Socialpoint, King, Rockstar, Funcom, Arrowhead, Fatshark,
> People Can Fly, Infinite Plus y MercurySteam.
> Se han reparado 2K, Respawn/EA, Epic, Room 8, Gram Games y Ember Lab, entre otras.
> Los apartados siguientes conservan la investigación anterior; para el estado actual consulta
> `SCANNER_DIRECTO.md`, `data/companies-registry.json` y `data/source-audit.json`.

Regla de oro (especificación §4): **no inventar identificadores ATS ni endpoints, y distinguir «evaluada» de «conectada»**.

## Cifras de la investigación inicial (históricas)

Las cifras de esta sección corresponden a la primera investigación. El estado actual
se genera en `data/companies-registry.json`; véase la revisión de pendientes de
`SCANNER_DIRECTO.md` para las incorporaciones y limitaciones verificadas hoy.

| Concepto | Valor |
|----------|------:|
| Empresas registradas (evaluadas + candidatas) | **71** |
| Con evidencia directa (escaneo de producción o investigación manual) | **30** |
| Configuradas en el scanner (`data/companies.json`) | **30** (eran 23) |
| Estado `active` (último escaneo real conectó con una API fiable) | 6 |
| Estado `pending` | 61 |
| Estado `unsupported` (no son estudios de juegos/VFX) | 4 |
| Estado `blocked` | 0 |

**La meta de «≥ 60 empresas evaluadas» NO se cumple como evaluadas: son 30 con evidencia directa.** Las otras 41 son
candidatas registradas como `pending`, sin conectar. Los números reales se determinan en ejecución: tras la primera
ejecución del workflow, el panel (*Empresas* y *Fuentes y scanner*) muestra el estado real de cada fuente.

Origen de la evidencia: `scanner-run` 23 (datos reales del escaneo del 2026-10-08), `web-research` 7 (investigación
del 2026-10-21 de este documento), `discovery-cache` 40 (tableros que el scanner de producción sondeó, **identidad
sin verificar**), `none` 1.

## Investigación del 2026-10-21 (páginas oficiales recuperadas ese día, salvo indicación)

### Mundfish — obligatoria · configurada
- Web oficial `https://mundfish.com/en/careers`: lista HTML con `VFX Artist #remote #senior` →
  `https://mundfish.com/careers/vfx-artist` y `Technical Artist #remote #middle`. Texto: «We support global remote work».
- **No usa ATS**: se solicita por email/Telegram. Sin tipo de contrato, salario ni fecha en la ficha.
- Integración: `MundfishAdapter` (`scanner/adapters/official_sites.py`), fuente poco fiable (HTML).
- Para tus criterios: remoto sí; **España no nombrada** → elegibilidad *posible*, contrato *desconocido*.
- El scraper genérico no la habría detectado (slug de un solo guion).

### AXIOM VFX — obligatoria · configurada
- Web oficial `https://www.axiomvfx.com/career`: una ficha «Real-Time VFX Artist» (Niagara/UE5), «Remote, flexible
  engagement — **full-time or contract**», sedes en **Austin (EE. UU.) y Valencia (España)**.
- Es un **estudio de servicios**: la contratación laboral no está acreditada. El panel muestra «ambiguo» con la frase
  literal, no «empleo».
- Integración: `AxiomVfxAdapter` (misma familia de adaptadores HTML).

### Larian Studios — configurada (Lever `larian`)
- Tablero visto en una oferta real (`jobs.lever.co/larian/…`) y presente en la caché de sondeo del scanner (dos
  evidencias independientes). Ofertas «Senior VFX Artist» en Dublín, Quebec y **Barcelona**, **presenciales**.

### IO Interactive — registrada (no configurada)
- Estudios en Copenhague, Malmö, **Barcelona**, Brighton y Estambul; VFX Artist (007 First Light) publicado en Barcelona.
  Las fichas están en `apply.ioi.dk/jobs/<id>-<slug>`; **no verifiqué qué ATS hay detrás** ni la URL del listado.

### Digital Sun Games — registrada (no configurada) · prioridad alta
- Valencia. Web propia `digitalsungames.com/jobs/<slug>/`. VFX Artist (Unity): **contrato indefinido, jornada completa,
  híbrido** (anuncio en Stratos, 2024-10-08); proceso «permanentemente abierto». Requiere adaptador propio (slug de una
  palabra). **Es la única con contratación laboral en España demostrada**, aunque híbrida.

### Escape Velocity Entertainment — registrada · prioridad alta
- Puestos VFX/Tech Art «Fully Remote», restricción «North America, Europe» (según Built In y Remotive).
  **Solo agregadores**: falta localizar su web oficial y su ATS.

### MercurySteam — registrada · prioridad baja
- Madrid, presencial. Anunció un proceso de ajuste de plantilla en mayo de 2026 (varios medios). Solicitud por email.

### Resto de la lista de la especificación
| Empresa | Situación |
|---------|-----------|
| Ubisoft (España/remoto) | Ya configurada (SmartRecruiters `Ubisoft2`, 7 ofertas el 08-10). **Falta filtrar por estudio/ubicación.** |
| Scopely | Configurada (Greenhouse `scopely`, tablero del sondeo). Verificar modalidad por vacante. |
| Saber Interactive Spain | Configurada (Personio, del sondeo). |
| Keywords Studios | Configurada (SmartRecruiters `keywordsstudios`). **No asumir empleo asalariado.** |
| Room 8 Studio | Ya en configuración como `custom` (scraper HTML); vigilar condiciones B2B. |
| 2K (genérico) | Configurada como `custom` (`2k.com/careers`); **falló en el último escaneo real** («No response»). |
| 2K Valencia / 31st Union | **Sin investigar.** Registrada como pendiente. |

## Qué NO está verificado

Ninguna de las fuentes nuevas se ha consultado **en vivo**: el entorno de pruebas no tiene acceso a internet para el
scanner. Mundfish y AXIOM se probaron contra HTML reconstruido a partir de las páginas oficiales (guardado en
`tests/fixtures/`), y las cabeceras de los tableros Lever/Personio/SmartRecruiters/Greenhouse con HTTP simulado.
El host `api.eu.lever.co` para tableros `jobs.eu.lever.co` está documentado por varias fuentes de terceros, no por
una llamada propia.

## Cómo comprobarlo tras subir los cambios

1. GitHub → *Actions* → «VFX Jobs Scanner» → *Run workflow*.
2. En el panel de admin → *Fuentes y scanner*: fuentes correctas/fallidas, peso de agregadores, duplicados fusionados.
3. En *Empresas*: las nuevas deben pasar de «Pendiente» a «Conectada» (o mostrar el error real).
4. Regenera el registro si cambias empresas: `python -m scanner.build_registry`.

## Cómo añadir una empresa

1. Localiza su página de empleo oficial y su ATS (la URL del tablero lo delata: `jobs.lever.co/<slug>`,
   `job-boards.greenhouse.io/<slug>`, `<slug>.jobs.personio.de`…).
2. Añádela a `data/companies.json` con `name` y `careersUrl` (el `type` se autodetecta; `custom` ya no anula un ATS conocido).
3. Si no tiene ATS, hace falta un adaptador propio (ver `official_sites.py` y su test con HTML de muestra).
4. `python -m scanner.build_registry` y `python -m pytest tests --ignore=tests/e2e`.
