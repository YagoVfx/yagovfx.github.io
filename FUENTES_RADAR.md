# Fuentes del radar móvil 0.7.0

Estado revisado el 24/10/2026. Los resultados no representan todas las vacantes de Internet.
Los portales complementarios no se etiquetan como ATS oficiales ni como verificación del empleador.

| Fuente | Estado real | Alcance |
| --- | --- | --- |
| Portales de estudios y ATS VFX existentes | Automático, sin cambios | Se mantiene el scanner directo VFX y su catálogo de empresas |
| Workable | Automático | Plain Concepts, Fabulous y EUROPEAN DYNAMICS; programación con remoto anunciado en España |
| Imatia | Automático, portal original | Desarrollo en A Coruña; excluye bolsas genéricas de talento |
| Inprosec | Automático, portal original | Software, soporte y SAP en Vigo; becas y requisitos para revisar |
| Sistema Nacional de Empleo | Automático | Municipio Vigo o A Coruña y búsquedas de remoto; no es un ATS |
| We Work Remotely | RSS público automático | Programación remota internacional/Europa; enlace y atribución al portal |
| Remote OK | API pública automática | Programación con región compatible; puede devolver cero resultados elegibles |
| Adecco | Comprobación automática de fichas seleccionadas | Actualmente instalaciones eléctricas en Vigo. No cubre todavía todo su buscador |
| eFundae | Automático | Cursos online de programación y electricidad/automatización |
| Microsoft Learn / dev.java | Recursos concretos seleccionados | Ruta C# y guía Java gratuitas; no son vacantes ni títulos reglados |
| Work With Indies, Hitmarker, GamesJobsDirect, ArtStation | Acceso manual desde VFX → Más fuentes | Descubrimiento complementario; no se importan como ofertas verificadas |
| Tecnoempleo, Manfred, Welcome to the Jungle | Acceso manual | Buscadores IT; no hay un conector automático implementado en esta versión |
| InfoJobs | Acceso manual; API pendiente de credenciales | [Registro oficial de aplicación](https://developer.infojobs.net/). Las credenciales privadas irían en GitHub Secrets, nunca en APK o JSON público |
| Emprego Xunta | Acceso manual | El formulario de empleo devuelve error al automatizar la consulta |
| Empléate, EURES, Manpower | Acceso manual | No se anuncia una integración automática sin validar |
| Randstad | Acceso manual | La consulta automatizada devuelve HTTP 403; no se intenta evadir el bloqueo |
| Xunta / DIPLOS / AFD 2026–2027, CNTG | Acceso manual | Convocatorias: comprobar modalidad, municipio, requisitos y matrícula abierta |
| Epic, Coursera, Udemy, TodoFP | Acceso manual | Catálogos complementarios; sin inventar plazas, precio, certificado o duración |

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
- Última consulta: 17 programación/soporte, 1 electricidad y 21 cursos automáticos; los filtros cambian
  el total visible. Hay además una ruta C# y una guía Java locales seleccionadas.

El workflow existente consulta el feed cada seis horas. Publicar el código y los datos en GitHub
activa la actualización de esta versión; el APK contiene una copia inicial válida.
