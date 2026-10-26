# Adecuación a DAM y electricidad en la app 0.16.0

Fecha: 26 de octubre de 2026.

## Corrección del problema

La búsqueda confundía relación temática con adecuación profesional. Que un anuncio mencionara electricidad no significaba que fuera un puesto de instalaciones eléctricas, y una oferta de ingeniería de datos no era una oportunidad de desarrollo DAM de entrada.

Se añaden estados separados de especialidad y nivel: perfil actual, requisitos por confirmar, reciclaje y fuera de perfil. La vista principal excluye reciclaje y fuera de perfil. Esas ofertas siguen accesibles mediante una selección explícita; las guardadas y las candidaturas históricas no desaparecen por este nuevo filtro. Cada ficha profesional incluye una razón legible.

- Analytics Engineer/Data, datos, arquitectura, SAP y DevOps no se presentan como desarrollo DAM de entrada.
- Electromecánica, motores diésel, mecatrónica y refrigeración se excluyen de la vista eléctrica principal. Una FP de otra especialidad no se trata como equivalente a electricidad.
- Oficina técnica que acepta grado superior queda como reciclaje: aceptar la titulación no acredita AutoCAD, herramientas de esquemas o experiencia de diseño.
- El título inglés Software Engineer no se descarta por sí solo: un desarrollador junior que acepte FP puede ser pertinente. Se revisan requisitos de estudios y experiencia, no solo el nombre del cargo.
- Mencionar que se trabajará con compañeros senior deja de clasificar automáticamente al candidato como senior.
- Los requisitos al final de las descripciones ya no se pierden con el límite anterior de 4.500 caracteres; se conserva más texto para revisarlos.

## Cobertura de programación

Se ha corregido el lector de Imatia/Inprosec: antes usaba el texto completo de la tarjeta como ubicación, en lugar de leer por separado título, ciudad y modalidad. Ahora recorre las páginas de sus tableros Bizneo y comprueba los requisitos completos. Imatia aporta un puesto mid e Inprosec/Greinfort uno que exige universidad; no se fuerzan a encajar con el perfil.

Se conecta Infortec Consultores mediante su tablero público Bizneo, con paginación y selección municipal/remota. Se han comprobado 15 anuncios de desarrollo. Se han releído también las descripciones de WWR, Sopra Steria y los tres tableros Workable.

El catálogo resultante contiene 31 anuncios de programación: 1 de nivel junior compatible por titulación con FP, 6 de reciclaje/experiencia previa y 24 fuera del perfil actual. El anuncio junior de Java exige conocimientos prácticos; no se afirma que el usuario cumpla todos sus requisitos ni que no haya más vacantes en el mercado. Es una cobertura parcial de fuentes concretas.

En electricidad se conservan 14 anuncios recopilados, pero solo 6 pertenecen a la vista principal de instalaciones/mantenimiento. Los otros 8 se separan por especialidad o necesidad de reciclaje. La cifra anterior de 14 no era una cifra de adecuación personal.

## Fechas y transparencia

Hay empresas que indican día y mes, pero no un año verificable. No se sustituye esa información por la fecha del escaneo. Esos anuncios quedan marcados como publicación sin fecha confirmada y no pasan automáticamente el filtro de último mes.

Se añade una opción explícita para incluirlos, con una advertencia de que no se consideran publicados en el período elegido. La lista ofrece esa acción cuando el filtro temporal puede ocultarlos.

## Validación y entrega

303 pruebas Python y 47 Flutter superadas, análisis sin incidencias y revisión de capturas de programación/electricidad. Cobertura móvil versión 10 para evitar que un feed anterior restablezca la selección incorrecta.

APK local: `mobile/dist/yago-vfx-jobs-0.16.0.apk`, excluida de Git. Hay que publicar código y datos juntos. La APK no se ha probado en un teléfono físico.

Queda pendiente conocer el año de finalización de DAM para evaluar ofertas de contrato formativo que puedan limitar la antigüedad del título. No se ha supuesto ese dato.
