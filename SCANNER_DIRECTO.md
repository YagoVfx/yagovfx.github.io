# Catálogo de portales directos

## UE, candidaturas privadas y cobertura (24-10-2026)

Web y Android 0.5.0 incorporan un filtro de Unión Europea basado en los 27 países, ciudades
reconocidas y ámbito UE explícito. «Europa» genérica no basta; Reino Unido, Suiza y Noruega
no se incluyen como miembros. El filtro es geográfico, no una prueba de permiso de trabajo.

Las candidaturas se almacenan en `users/{uid}/applications/{jobId}`, nunca en el JSON del
portfolio ni en GitHub. Web y móvil usan el mismo documento por ID de oferta, con fecha,
estado y notas; también permiten registrar envíos anteriores manualmente. La cuenta debe
ser la misma cuenta Firebase administradora. Hay sincronización cada 15 segundos, al abrir
la pantalla y al actualizar. Guardadas y descartadas siguen siendo locales. Las reglas
`firestore.rules` limitan lectura y escritura al propietario autorizado y validan los campos.
`scripts/test-firestore-rules.cjs` verifica esas reglas contra un proyecto de emulación.

Se añaden **SNK** (Workable oficial), **Capcom** (HRMOS enlazado por su web) y **Rovio**
(listado propio, con presencia en Barcelona). Capcom publica un puesto de efectos cuyo
título japonés se conserva junto a la traducción VFX Artist. SNK y Rovio no presentaron
coincidencias VFX activas en los feeds examinados. En SNK no se importan roles VFX que
solo permanecen en comentarios HTML antiguos o menús del sitio.

**Saber Interactive Spain ya está conectado** mediante Personio. Su portal declara no
tener vacantes; se añade su sede verificada de Alcobendas al mapa y el país ES al catálogo.
No se convierte por ello en una fuente global de todos los estudios del grupo Saber.

La auditoría española incorpora Piccolo Studio, Abylight, Chibig, Crema, Novarama,
Péndulo Studios, The Breach Studios y Fictiorama, con la limitación real de cada portal.
Las primeras webs no ofrecen un feed verificado que permita declararlas conectadas;
las restantes muestran errores de certificado, página de error o cierre de conexión.
No es un censo exhaustivo de todos los estudios españoles.

Última pasada: 73 fuentes configuradas, 70 consultas correctas, 66 ofertas activas oficiales.
Blizzard, Activision y King devolvieron HTML donde su API Workday esperaba JSON; se conserva
el historial en vez de cerrar ofertas por ese fallo. El registro distingue esos errores.
El mapa contiene 57 de 96 empresas localizadas, excluidas las entidades fuera de perfil.

## Radar global: mapa y plataformas

Web: pestaña **Mapa y estadísticas**, tanto pública como del administrador. Android 0.4.0:
pestaña **Radar**. La gráfica circular agrupa las ofertas oficiales activas por la plataforma
real de cada fuente configurada (por ejemplo, Room 8 como WordPress aunque su adaptador
normalice los anuncios como `custom`). Cuenta las coincidencias posibles, excluye agregadores
y cerradas y no depende de los filtros personales. Las plataformas configuradas con cero
ofertas siguen visibles; las sedes que comparten portal no duplican los anuncios.

Room 8 ya estaba integrado: el JavaScript público de su web consulta los mismos feeds
`/wp-json/wp/v2/talent` de room8group.com y room8studio.com que usa el adaptador. Hexworks
figura como estudio de CI Games con portal compartido, sin otra consulta ni anuncios duplicados.
Fuentes: https://room8group.com/join-the-team/ y https://cigames.com/en/contact/.

`scanner.map_locations` genera `data/company-locations.json` desde ubicaciones estructuradas
de portales públicos, ofertas y páginas oficiales de contacto. Esta revisión localiza **50 de
85 empresas del catálogo**; las demás se listan sin ubicación verificada. Son puntos urbanos
aproximados, no domicilios exactos, un censo completo de sedes ni una prueba de trabajo remoto.
El workflow actualiza estos datos tras cada escaneo. No utiliza geolocalización del usuario.

`data/world-map.json` contiene la cartografía Natural Earth (dominio público), proyectada
sin servicios externos de mapas. La APK incluye la misma cartografía y una copia inicial
del catálogo; después descarga las ubicaciones actualizadas y conserva caché local.
Para refrescar la copia que se incluye en una nueva APK, copiar los JSON de empresas y
ubicaciones a `mobile/assets/` antes de compilar.

La revisión 0.4.0 agrupa marcadores por su proximidad en pantalla. La web admite arrastre,
rueda, doble clic, pellizco y teclado; pulsar un grupo muestra sus empresas en un panel
legible y acerca la zona cuando las ubicaciones son distintas. La app permite arrastre,
pellizco y doble toque, con una lista inferior al pulsar grupos y enfoque al seleccionar
una empresa. Los nombres ya no se dibujan simultáneamente sobre todos los puntos.
Una empresa puede aparecer en varias zonas porque tiene más de una ubicación.

Desde 0.4.1, pulsar un punto verde muestra únicamente las ubicaciones de ese marcador
sin cambiar la cámara ni filtrar el mapa a todas las sedes de la empresa. La acción
«Ver todas sus sedes» realiza ese enfoque explícitamente en web y Android.

El enlace Jobs VFX Scanner en GitHub aparece en la cabecera de todos los paneles web
y en Radar de Android. Abre el workflow; no ejecuta ni publica nada desde la interfaz.

## Revisión de pendientes y cobertura española (23-10-2026)

El catálogo pasa de 59 a **70 fuentes configuradas**. Se incorporan Highdive,
MobilityWare, Socialpoint, King, Rockstar Games, Funcom, Arrowhead Game Studios,
Fatshark, People Can Fly, Infinite Plus y MercurySteam. La primera ejecución
consultó las 70 sin errores y obtuvo **65 ofertas activas oficiales**; Highdive
aportó una vacante de Principal VFX Artist. Conectar una fuente no significa
que tenga puestos de VFX actuales ni que admita trabajar desde España.

- **MobilityWare:** el HTML bloquea al bot, pero su API pública Greenhouse funciona.
- **Infinite Plus:** seis descripciones publicadas en su web propia, ninguna de VFX.
  El adaptador conserva que son anuncios inline sin inventar URLs de detalle.
- **MercurySteam:** su página de talento declara explícitamente que no hay posiciones
  abiertas. Si desaparece esa declaración, se pide revisar el nuevo listado en lugar
  de interpretar cualquier HTML como una lista vacía.
- **Funcom:** Teamtailor publica explícitamente «No open positions right now».
  Se distingue esa declaración de una página que simplemente no carga sus anuncios.
- **Digital Sun y Cactus Punch:** siguen bloqueadas (403/401); no hay una conexión
  recuperada mientras sus datos no se puedan consultar. El índice WordPress público
  de Digital Sun no implica acceso a sus rutas de datos, que devuelven 401.
- **Company 3:** portal oficial JazzHR localizado; integración pendiente de separar
  puestos de tiempo real de cine/postproducción. Se descarta la candidata Recruitee.
- **Airship Syndicate y Genius Game FZCO:** web oficial identificada, sin listado
  público de vacantes verificable. **Iris Games:** identidad aún sin acreditar.

En España se añaden Socialpoint y MercurySteam; King se consulta globalmente y la
ubicación se comprueba por anuncio. Ubisoft, Activision/Digital Legends, IOI, Larian,
Scopely, Gameloft, Saber y 2K/31st Union ya estaban cubiertas por sus fuentes actuales;
no se duplica un tablero por cada sede. Se registran también **The Game Kitchen** y
**Secret 6** (bloqueadas), **Nomada Studio** (sin vacantes según su web, integración
pendiente) y **BlitWorks** (contacto manual, sin listado público verificable).

No es un censo exhaustivo de estudios españoles o internacionales. El registro incluye
también estudios investigados sin ATS conocido; cada uno conserva el motivo concreto.
Los apartados siguientes documentan la ampliación anterior de 30 a 59 fuentes.

## Ampliación de cobertura del 23-10-2026

La segunda revisión amplía las fuentes configuradas de 30 a 59. El escaneo real final
consultó las 59 sin errores ni resultados truncados: 64 ofertas activas oficiales, 52
visibles por defecto y otras 12 al activar coincidencias posibles. Son anuncios de fuentes
directas; esa verificación no garantiza que se pueda trabajar desde España.

- 2K pasa del scraper genérico a Greenhouse. Se conectan también 31st Union, Cloud Chamber,
  Hangar 13 y Gearbox con identificadores enlazados o embebidos por sus webs oficiales.
- Respawn se consulta en el portal EA, con búsqueda paginada y verificación de estudio tanto
  en el listado como en la ficha. El escaneo final encontró tres vacantes de Respawn.
- Epic usa su API pública real, con paginación `limit/skip` y validación del total. No encontró
  puestos VFX en sus 171 anuncios actuales; no se añaden vacantes antiguas del agregador.
- Room 8 usa los feeds WordPress de sus dos webs, y Ember Lab su feed BambooHR. Sus listas
  actuales no tienen coincidencias VFX; la conexión funciona aunque no haya vacantes relevantes.
- Build A Rocket Boy usa el JSON de su portal Pinpoint; devuelve una lista vacía válida.
- Entre las nuevas fuentes: Riot, Naughty Dog, Digital Extremes, Deck13, Blackbird, Velan,
  Liquid Development, Believer, Voodoo, Hasbro, Insomniac, Asobo, Homa, Cloud Imperium y Gram Games.
- La identidad de las candidatas restantes se documenta en `data/source-audit.json`. Se retiran
  enlaces a empresas homónimas y al agregador Jobgether, y se distinguen los bloqueos HTTP 403.

### Qué significa la cifra antigua

La revisión del JSON anterior en Git encontró 317 registros de agregadores: 57 activos,
259 con estado `unverified` y uno cerrado. No eran 317 vacantes oficiales confirmadas.
Incluían duplicados de empresa, agencias, empresas ajenas al perfil y puestos que ya no
aparecen en los portales actuales. La recuperación consulta el portal de cada empleador;
no convierte automáticamente los registros antiguos en ofertas oficiales.

### Web y APK

Ambas consumen `https://yagovfx.github.io/data/jobs.json`. Al publicar los datos y el scanner
actualizados, la APK 0.2.0 recibe las nuevas ofertas al actualizar: no necesita recompilarse
para añadir empresas. Los cambios de interfaz/filtros de la web no modifican automáticamente
los widgets de Flutter. Guardadas y descartadas siguen siendo locales en cada dispositivo.

Las empresas se configuran para el scanner en `data/companies.json`; editar una lista en
el admin de Firebase no modifica ese archivo de GitHub por sí solo.

---

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
