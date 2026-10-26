# Cobertura filtros y ajustes de la app 0.15.0

Fecha de comprobación: 26 de octubre de 2026.

## Resultados comprobados

| Apartado | Catálogo incluido | Vista inicial comprobada |
| --- | --- | --- |
| Programación | 13 ofertas | 3 con los filtros iniciales; otras requieren revisar experiencia o titulación |
| Electricidad | 14 ofertas | Incluye experiencia eléctrica previa; los requisitos específicos siguen pendientes de revisión por el usuario |
| Cursos | 47 automáticos y 5 de selección fija | 39 con los filtros iniciales y todas las especialidades |
| Oposiciones | 247 registros oficiales examinados, 4 convocatorias relacionadas seleccionadas | 1 municipal en Vigo/A Coruña; 4 al consultar toda España |

Los recuentos son de esta comprobación y pueden variar. No representan todas las vacantes o convocatorias existentes en España.

## Ofertas y cursos

Se añaden tres lectores automáticos de portales originales: Sopra Steria mediante SmartRecruiters (4 ofertas remotas de desarrollo), Cofrico mediante Viterbit (1 puesto técnico en Vigo), y Randstad (11 ofertas eléctricas o de mantenimiento en Vigo/A Coruña). Randstad es una agencia y no se presenta como empleador directo; el cliente puede no estar identificado. Los anuncios de frigorista y mantenimiento pueden exigir acreditaciones, movilidad o formación específica adicional.

La ruta de A Coruña se ha validado contra la web de Randstad. Se filtra la localidad de cada ficha y se conservan las fechas originales de publicación. No se importan empleos de otros municipios por pertenecer a la misma provincia.

Elecnor se ha investigado: su portal Epreselec presentó una comprobación antiautomatización. No se ha sorteado ni se anuncia una conexión operativa inexistente. Cofrico sí se ha conectado y probado.

Programación deja de arrancar exclusivamente en «Para empezar», que ocultaba ofertas con requisitos todavía por revisar. Se mantiene la exclusión inicial de experiencia alta y universidad obligatoria. Se puede filtrar el conjunto por empresa.

Cursos arranca con todas las especialidades. Se distinguen filtros de centro/proveedor y procedencia, de modo que puede seleccionarse Xunta/DIPLOS aunque el curso lo imparta otro centro. Se ha corregido el uso del nivel de cualificación profesional de DIPLOS como si indicara dificultad avanzada: los requisitos de acceso se conservan, pero esa cifra no basta para ocultar el curso como avanzado.

Las copias guardadas se comparan con la fecha de actualización parcial del paquete. Una caché anterior ya no sustituye una copia incluida más reciente. Los feeds móviles pasan a coverageVersion 9 y el de oposiciones a coverageVersion 2; los formatos anteriores no sustituyen los nuevos datos al actualizar.

## Oposiciones

Se usa el mismo endpoint POST y los mismos límites que el botón oficial «Exportar XML» del PAG. Esto evita depender del fragmento de búsqueda GET que estaba devolviendo respuestas cacheadas inconsistentes. Se procesan las descripciones específicas, no solo títulos genéricos como «Técnico Superior».

Se comprueban acceso libre, plazas libres, nivel de titulación y un período de solicitud actualmente abierto. Si hay ampliaciones de plazo se conserva el período vigente. Se excluyen procesos con cero plazas de acceso libre, cerrados, futuros o de nivel universitario incompatible. La fuente sigue siendo informativa: las bases y sus modificaciones prevalecen.

La administración convocante se filtra aparte de la ubicación: estatal, autonómica, local, universidades u otras. Al escoger autonómica o estatal desde el ámbito municipal se abre el ámbito a toda España, dejando visible esa selección. En esta descarga concreta no se encontró una estatal que pasara los criterios del perfil; no se afirma que no existan otras oportunidades.

Fuentes oficiales y originales utilizadas:

- PAG: https://administracion.gob.es/empleopublico/resultados-empleo
- Exportación: https://administracion.gob.es/content/sling/endpoints/pag/front-elastic/empleo-elastic/exportar
- Randstad Vigo: https://www.randstad.es/candidatos/ofertas-empleo/p-pontevedra/c-vigo/
- Randstad A Coruña: https://www.randstad.es/candidatos/ofertas-empleo/p-coruna/c-coruna-a/
- Cofrico: https://cofrico.viterbit.site/
- Sopra Steria: https://api.smartrecruiters.com/v1/companies/SopraSteria1/postings

## Ajustes generales

Ahora se pueden cambiar el tamaño del texto, la densidad de las tarjetas, la categoría inicial y la actualización automática al abrir. Se guardan en el dispositivo y se restauran al reiniciar. El tamaño de texto respeta el tamaño configurado en el sistema y aplica una ampliación adicional. La sincronización privada de candidaturas mantiene su funcionamiento independiente.

## Validación y publicación

298 pruebas Python y 45 Flutter superadas, más revisión de capturas de pantallas y filtros. Análisis de Flutter sin incidencias. No se ha probado la APK en un teléfono físico.

APK local: `mobile/dist/yago-vfx-jobs-0.15.0.apk`. No se suben instaladores ni ZIP a Git. Hay que publicar código y datos juntos para que el scanner y el servidor usen los nuevos formatos. Las conexiones nuevas no se han ejecutado aún desde GitHub Actions; sí desde este equipo.
