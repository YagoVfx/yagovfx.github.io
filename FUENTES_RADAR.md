# Fuentes del radar móvil 0.8.0

Estado revisado el 24/10/2026. Los resultados no representan todas las vacantes de Internet.
Los portales complementarios no se etiquetan como ATS oficiales ni como verificación del empleador.

| Fuente | Estado real | Alcance |
| --- | --- | --- |
| Portales de estudios y ATS VFX existentes | Automático, sin cambios | Se mantiene el scanner directo VFX y su catálogo de empresas |
| Workable | Automático | Plain Concepts, Fabulous y EUROPEAN DYNAMICS; programación con remoto anunciado en España |
| Imatia | Automático, portal original | Desarrollo en A Coruña; excluye bolsas genéricas de talento |
| Inprosec | Automático, portal original | Software, soporte y SAP en Vigo; becas y requisitos para revisar |
| Indra / Minsait | Automático, SuccessFactors | Búsquedas de Vigo, Coruña y remoto; solo se importan ubicaciones o teletrabajo que constan en la ficha |
| Inditex / Zara | Automático, Recruitee | Puestos técnicos concretos; excluye bolsas «Join us» y programas genéricos. Confirmar si la sede anunciada como Coruña es Arteixo |
| Veolia | Automático, SmartRecruiters, con paginación | Mantenimiento eléctrico en las ciudades objetivo; descarta títulos que señalan Bergondo u otros municipios aunque los metadatos digan Coruña |
| Sistema Nacional de Empleo | Automático | Municipio Vigo o A Coruña y búsquedas de remoto; no es un ATS |
| We Work Remotely | RSS público automático | Programación remota internacional/Europa; enlace y atribución al portal |
| Remote OK | API pública automática | Programación con región compatible; puede devolver cero resultados elegibles |
| Adecco | Comprobación automática de fichas seleccionadas | Actualmente instalaciones eléctricas en Vigo. No cubre todavía todo su buscador |
| eFundae | Automático | Cursos online de programación y electricidad/automatización |
| Microsoft Learn / dev.java | Recursos concretos seleccionados | Ruta C# y guía Java gratuitas; no son vacantes ni títulos reglados |
| Work With Indies | Automático, RSS y ficha | Comprueba el aviso real de cierre; no confunde un banner oculto de la plantilla con una oferta cerrada |
| Hitmarker | Automático, búsqueda pública | Consulta el índice público de ofertas abiertas con su clave de búsqueda pública temporal; no usa cuentas ni la publica en el feed |
| GamesJobsDirect | Automático, búsqueda y ficha | Lee las fichas JobPosting, tolerando la puntuación JSON inválida del proveedor; comprueba vencimiento |
| Stratos | Automático, RSS oficial y listado de trabajo | Solo categoría Trabajo y roles VFX/Technical Art aún listados, con fecha de hasta 120 días; excluye noticias y colaboraciones. Se identifica freelance y remuneración aplazada si se anuncia |
| ArtStation | Intento automático fallido | HTTP 403 en el endpoint público; no se evaden controles ni se presentan anuncios como importados |
| Tecnoempleo, Manfred, Welcome to the Jungle | Acceso manual | Buscadores IT; no hay un conector automático implementado en esta versión |
| InfoJobs | Aplazado por decisión del usuario | No se solicitan credenciales ni se desarrolla este conector en esta versión |
| Emprego Xunta: ofertas privadas | Intento automático fallido | Se carga el formulario y sus campos actuales. El POST oficial devuelve HTTP 400 «provided host name is not valid». Se muestra el fallo; no se convierte en cero ofertas |
| Empléate, EURES, Manpower | Acceso manual | No se anuncia una integración automática sin validar |
| Randstad | Acceso manual | La consulta automatizada devuelve HTTP 403; no se intenta evadir el bloqueo |
| Xunta / DIPLOS | Automático, API pública | Familias ELE, IFC, IMS e IMA; paginación y acciones formativas concretas. Solo Vigo/Coruña o teleformación; excluye cursos ya empezados. Planificado no significa plazas abiertas |
| CNTG | Automático, listado y ficha | Solo plazo anunciado abierto y modalidad virtual/teleformación; excluye formación presencial de Santiago y solicitudes vencidas |
| Epic y SideFX | Selección de recursos concretos | Curso introductorio Niagara, guía práctica Niagara y Houdini Foundations 20.5 con aviso de versión |
| Coursera, Udemy, TodoFP | Acceso manual | Catálogos complementarios; sin inventar plazas, precio, certificado o duración |

También se investigaron los buscadores completos de Adecco y Eurofirms: Adecco devolvió errores HTTP 500,
IndexOutOfRangeException o resultados vacíos no validados según el endpoint; Eurofirms HTTP 503.
No se declara descubrimiento completo para esos buscadores. Adecco sigue limitado a sus fichas seleccionadas.

## Criterios de inclusión

- Vigo y A Coruña son ciudades, no toda su provincia. No se considera Cambre como A Coruña
  ni Redondela como Vigo. Las ofertas eléctricas requieren localidad explícita.
- Remoto no equivale a todo el mundo: se requiere región global/Europa/España y se descartan
  restricciones explícitas detectadas a otros países. La ficha sigue pidiendo confirmar elegibilidad.
- Los puestos con mucha experiencia se muestran con advertencia y pueden ocultarse. Una beca puede
  requerir convenio o matrícula: el texto original permite revisar esas condiciones.
- Antigüedad usa fecha publicada; no usa la fecha de escaneo. Las ofertas cerradas/retiradas se excluyen.
- Ante fallo de una fuente se conserva su copia anterior, con aviso y fecha original. Una respuesta
  HTTP 404/410 de una ficha Adecco confirma que fue retirada y no se mantiene como oportunidad activa.
- Última consulta: 23 programación/soporte, 2 electricidad, 179 anuncios VFX complementarios y 38 cursos
  automáticos (21 eFundae, 16 DIPLOS y 1 CNTG). Hay además cinco recursos seleccionados: dos de programación
  y tres de VFX. Los portales pueden repetir vacantes de los estudios: esos 179 anuncios no se suman al
  contador de ofertas directas como si fueran vacantes nuevas verificadas.

## Selección de formación

La app separa VFX, Electricidad y Programación. Ordena por encaje para retomar la especialidad:
nivel inicial, coste, duración acotada, relación del título con la especialidad, programa disponible y
plazo abierto. Penaliza nivel avanzado y comprobación antigua tras un fallo; explica cada criterio en
la ficha. No son reseñas ni una evaluación de la calidad docente, ni garantizan contratación o admisión.

Para empezar se priorizan fundamentos eléctricos de 70 horas en Vigo, repaso C#/Java y recursos oficiales
de Niagara/Houdini. Los cursos de 500–600 horas siguen disponibles, pero se avisa de su dedicación.
El dato de certificación de CNTG remite a las condiciones de examen y asistencia de cada ficha.

El workflow existente consulta el feed cada seis horas. Publicar el código y los datos en GitHub
activa la actualización de esta versión; el APK contiene una copia inicial válida.

Actualización parcial posterior: Stratos aporta tres anuncios (FrameOver, MercurySteam y Digital Sun Games).
Se conserva la fecha de publicación original y se registra la comprobación de cada ficha; no se presentan
como recién publicados. El RSS específico `https://stratos-ad.com/rss?source=jobs` responde HTTP 200 al lector
identificado del scanner. Una petición genérica anterior recibió HTTP 403 con otro contenido; un 403 real
del lector seguirá siendo un error y no se convertirá en una búsqueda vacía.

Los ATS se usan también fuera de VFX: Workable, Recruitee (Inditex) y SuccessFactors (Indra/Minsait) en
programación, y SmartRecruiters (Veolia) en electricidad. El siguiente aumento de cobertura requiere
conectar más empleadores concretos; no existe un feed ATS universal de todos los electricistas o programadores.
# Actualización 0.9.0 — 25/10/2026

Los conectores publican categorías y plataforma en el estado de fuentes. La app permite consultar estadísticas de programación, electricidad y cursos, además del scanner VFX directo. Los recuentos de importación no se presentan como ofertas compatibles ni como número de vacantes de todo un ATS.

La formación incorpora comprobación automática de cuatro lecciones seleccionadas de SideFX: Fluid FX for Realtime, Realtime Destruction Techniques, How to Export to PCG in Unreal y Procedural Assets for Unreal. Se conserva la distinción entre cursos, tutoriales y guías. La prioridad depende del objetivo Repasar / Mejorar / Aprender algo nuevo, sin puntuaciones inventadas de calidad docente.

Las fichas de empleo móvil diferencian grado universitario obligatorio, FP/experiencia equivalente y requisitos no confirmados. La detección es conservadora y no sustituye la lectura del anuncio; el título “Software Engineer” por sí solo no requiere universidad.
