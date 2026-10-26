# Fuentes y cursos de la app 0.13.0

Fecha: 26 de octubre de 2026. Segunda fase de las correcciones de las auditorías.

## Qué se ha comprobado en directo

Se han consultado los formularios públicos de SNE para electricista, electric y telecomunicaciones en Vigo y A Coruña. Esas consultas devolvieron cero. Instalador devolvió una ficha de gas en A Coruña, no una vacante eléctrica. No se ha importado para aumentar artificialmente la cobertura. Esto comprueba esas consultas concretas, no demuestra que no exista trabajo eléctrico en los municipios.

El resultado real de SNE usa también «Coruña, a (Coruña (a))». Se ha ampliado la normalización a ese formato. Una respuesta con cabecera de resultados pero sin filas reconocibles ni aviso explícito de cero pasa a considerarse error de formato.

DIPLOS y CNTG respondieron correctamente desde este equipo. Sus lectores completos produjeron 17 y 1 cursos respectivamente, aplicando los filtros de modalidad, municipio y fechas. No se ha probado aún la accesibilidad de esos servidores desde GitHub Actions, por lo que no se afirma que sus timeouts estén resueltos permanentemente.

El PAG inicialmente devolvió dos convocatorias para informática y cero para electricidad y una consulta inexistente. Al repetirlo devolvió el mismo fragmento vacío para consultas diferentes. Las cabeceras indicaban respuestas reutilizadas desde CloudFront con la misma fecha y antigüedad, incluso al variar los parámetros. Esa evidencia apunta a una caché que impide confiar en el resultado; no permite atribuir con certeza el fallo a toda la infraestructura del PAG.

El scanner ya no elimina convocatorias previas dentro de plazo cuando todas las consultas pasan repentinamente a cero: conserva las fichas sin renovar su comprobación y emite un aviso de coherencia. Las dos fichas conservadas están marcadas como retenidas, y la de Castellón sigue fuera del filtro municipal por defecto. La comprobación de la sede de Vigo encontró tres procesos relacionados fuera de plazo de solicitud.

Fuentes oficiales utilizadas:

- SNE: https://www.sistemanacionalempleo.es/OfertaDifusionWEB/busquedaOfertas.do?modo=inicio
- DIPLOS: https://diplos.xunta.gal/diplos/api/search?familia=ELE&pag=1
- CNTG: https://cntg.xunta.gal/gl/actividades/buscar-cursos?field_plazo_abierto_value=1&page=0
- PAG: https://administracion.gob.es/empleopublico/resultados-empleo
- Vigo: https://sede.vigo.org/expedientes/oposicions/ofertas_tipo.jsp?id=2&lang=es&tipo=1

## Cambios visibles

Los cursos se separan en VFX y videojuegos, programación, electricidad, telecomunicaciones y herramientas digitales. Excel, competencias digitales y ChatGPT no se presentan como desarrollo de software por pertenecer a la familia IFC. La familia eléctrica ELES y los cursos microinformáticos se distinguen como telecomunicaciones. Los temas aparecen también con nombres legibles en las estadísticas.

Se han sustituido los 17 cursos retenidos de Xunta por las 18 fichas consultadas ahora. El catálogo automático contiene 47 recursos: 18 de programación, 10 de electricidad, 9 de herramientas digitales, 8 de VFX y 2 de telecomunicaciones. A esto se añaden los recursos de selección fija existentes. Los recuentos no garantizan plazas, inscripción ni acceso por titulación.

La paginación de DIPLOS deja de presuponer 50 registros por página. Comprueba el número recibido y detecta páginas repetidas o vacías antes de completar el total. Los códigos de especialidad pueden repetirse en acciones formativas distintas: no se usan como contador de cursos únicos.

ArtStation y el formulario de empleo privado de Xunta se muestran como integraciones pendientes, distintas de una caída temporal de una fuente operativa. No se anuncian como nuevas conexiones ni se reintenta periódicamente un adaptador todavía sin validar. El diagnóstico de Xunta se conserva como función explícita independiente. SNE, DIPLOS y CNTG mantienen sus consultas separadas.

Las estadísticas usan la última consulta correcta de cada fuente cuando está disponible y señalan que la actualización del catálogo puede ser parcial. La actualización de cursos no renueva las fechas de las ofertas de trabajo.

## Validación y publicación

295 pruebas Python, 27 JavaScript y 39 Flutter superadas; análisis de Flutter sin incidencias. No se ha ejecutado la APK en un teléfono físico.

Versión 0.13.0+14, feed móvil coverageVersion 8. Subir código y JSON juntos para que el servidor no reponga el formato anterior. APK local en `mobile/dist/yago-vfx-jobs-0.13.0.apk`; los instaladores y ZIP siguen excluidos de Git.

Siguen pendientes el descubrimiento eléctrico en más empresas, la simplificación completa de navegación, la agrupación de itinerarios formativos repetidos, más contenido formativo de pago ajustado al presupuesto y las variantes de identidad de ATS todavía no cubiertas. La protección conservadora del PAG no repara su caché externa: evita presentar una desaparición de resultados como un cierre confirmado.
