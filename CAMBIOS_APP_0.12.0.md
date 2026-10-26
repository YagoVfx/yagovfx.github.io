# Correcciones de la app 0.12.0

Primer bloque de correcciones de las auditorías externas, 26 de octubre de 2026.

## Cambios

- «Persona responsable» deja de marcar una oferta como experiencia alta. Se conservan señales explícitas como senior, jefe o años de experiencia.
- El filtro de remoto rechaza las variantes comprobadas de restricción a EE. UU. y Hong Kong, y descripciones de teletrabajo limitado a uno o dos días semanales. No constituye un clasificador completo de todos los países ni sustituye revisar las condiciones.
- Se reconocen Teis, Bouzas, Zona Franca y Balaídos dentro de Vigo, y el alias «Coruña, A», manteniendo fuera otros municipios.
- Mejor detección de formación universitaria y grado medio/superior. Las preferencias expresadas como valorables no se convierten automáticamente en obligación.
- La experiencia eléctrica se muestra por defecto; los requisitos universitarios siguen sujetos al filtro de perfil.
- Los cursos con una convocatoria ya iniciada y sin evidencia de inscripción abierta dejan de ofrecerse como nuevas oportunidades. Se conservan los de matrícula continua o plazo todavía abierto.
- Tarjetas con fecha de comprobación y aviso visible de datos retenidos tras errores. Las oposiciones retenidas también lo indican.
- Un fallo total del scanner no renueva `updatedAt`. `lastAttemptAt` registra el intento y las fuentes móviles incorporan `lastSuccessAt` cuando hay evidencia nueva; no se inventan fechas históricas.
- Corrección de la coincidencia por URL de Workable en candidaturas web. Se conserva el registro anterior con notas y estado.
- Las variantes de URL de SmartRecruiters con el mismo empleador e ID se unifican sin confundir requisiciones diferentes.
- La sincronización periódica móvil no consulta en segundo plano y se actualiza al volver. El error web 403 deja de afirmar que necesariamente faltan reglas por publicar.
- Radar ya no sustituye silenciosamente oposiciones por programación. Se explica dónde consultar las plazas y fuentes.
- Texto corrupto de búsqueda corregido y errores técnicos crudos retirados del resumen de cobertura.

## Datos y despliegue

Se han reclasificado los datos existentes sin afirmar una consulta nueva: permanecen sus fechas de comprobación originales. El feed y su copia incluida en la APK pasan a `coverageVersion=7`; la app rechaza feeds anteriores para evitar que el servidor reponga los casos conocidos hasta publicar estos cambios. Hay 198 ofertas complementarias y 46 cursos; la reducción no acredita cierres de vacantes, responde al filtrado y unificación.

Subir código y datos juntos desde GitHub Desktop, y ejecutar un nuevo scanner desde main. La APK se guarda en `mobile/dist/yago-vfx-jobs-0.12.0.apk`, directorio ignorado por Git. No se han cambiado las reglas de Firebase ni publicado nada remotamente.

## Validación y pendientes

281 pruebas Python, 27 JavaScript, 39 Flutter y 6 pruebas de navegador de candidaturas superadas. El análisis de Flutter no presenta incidencias. La APK no ha sido probada en un teléfono físico.

Siguen pendientes la comprobación de SNE y PAG contra búsquedas reales, la causa de los errores de Xunta, el descubrimiento eléctrico más amplio, otras identidades ATS como Workday, la selección más precisa de cursos y la simplificación general de navegación. No se consideran resueltos por este bloque.
