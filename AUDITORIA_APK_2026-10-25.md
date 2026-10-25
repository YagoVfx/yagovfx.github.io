# Auditoría de la app 0.8.0 — 25/10/2026

Alcance: revisión del código Flutter, selección de ofertas, catálogo, datos locales y JSON incluido dentro de `mobile/dist/yago-vfx-jobs-0.8.0.apk`. No se ha realizado una sesión de uso en un teléfono ni una comprobación actual de vacantes en Internet. No se modifica el comportamiento de la aplicación en esta auditoría.

## Hallazgos prioritarios

| Prioridad | Hallazgo comprobado | Consecuencia | Cambio propuesto |
|---|---|---|---|
| Alta | Las categorías adicionales presentan explicación, fecha, buscador, interruptores, selectores y estado de fuentes en el mismo listado. Las fichas también muestran requisitos, avisos y varias acciones. | Mucha lectura antes de comparar oportunidades. | Cabecera breve, buscador, botón Filtros y contador; fichas resumidas y detalle al pulsar. Fuentes y explicaciones en una pantalla aparte. |
| Alta | De 23 ofertas de programación del feed local, 15 están marcadas con experiencia alta, 6 como desconocida y solo 2 como junior. Se incluyen avanzadas por defecto. | La cantidad disponible aparenta más oportunidades adecuadas de las que hay. | Vista inicial de perfiles de entrada y FP; separar requisitos desconocidos y experiencia alta. No rebautizar desconocido como compatible. |
| Alta | La clasificación detecta palabras de ingeniería y muestra una advertencia, pero no distingue un grado obligatorio de una titulación alternativa o un nombre de puesto. | Puede admitir ofertas que exigen universidad y generar dudas en ofertas accesibles con DAM. | Extraer requisito, obligatoriedad y evidencia: FP admitida, universidad obligatoria, experiencia equivalente o sin confirmar. No excluir solo por “Software Engineer”. |
| Alta | La prioridad de cursos suma 30 por nivel inicial, 10 por repaso y resta 15 por avanzado; además el nivel avanzado se oculta inicialmente. | La recomendación está orientada a retomar, no a progresar o cambiar de especialidad. | Objetivos elegibles: Repasar, Mejorar y Aprender algo nuevo. Adaptar el orden al objetivo y conservar avisos de prerrequisitos. |
| Alta | Los 38 cursos automáticos son de programación/electricidad; ninguno tiene temática VFX. Hay tres recursos VFX seleccionados en el catálogo fijo. | La pestaña VFX de cursos tiene cobertura muy limitada y no es un catálogo automático de formación de videojuegos. | Ampliar cursos concretos de VFX y videojuegos; distinguir curso, tutorial y guía. No contabilizar páginas generales como cursos. |
| Media | `InsightsPage` recibe únicamente las ofertas del scanner VFX directo y su catálogo de empresas. | No existen estadísticas integradas de programación, electricidad o formación. | Selector de especialidad y formación, con procedencia, ATS, empresas, estado de consulta y resultados pertinentes. |
| Media | El estado de fuentes del listado muestra todas las fuentes del feed sin seleccionar la categoría. | Una fuente ajena distrae y puede confundirse con cobertura de esa profesión. | Asociar cada fuente a categorías explícitas; mostrar solo las correspondientes y distinguir conectada sin resultados de fallida. |
| Media | El esquema de fuentes no normaliza ATS, empresa y categoría; hay nombres combinados y mezcla de `examined` y `matched`. | Los recuentos no sirven directamente para comparar cobertura. | Campos explícitos de categoría, plataforma, empresa, tipo, fecha y estado. Separar examinadas, importadas, vigentes y compatibles. |

## Perfil que debe orientar la selección

- Formación indicada por el usuario: FP2/DAM, electricidad y electrónica, y telecomunicaciones. No consta titulación universitaria.
- Programación: entrada profesional, DAM, desarrollo de aplicaciones, QA inicial y soporte técnico relacionado; Vigo, A Coruña y remoto compatible con residencia en España.
- Electricidad/electrónica/telecomunicaciones: aprovechar experiencia previa en alumbrado, instalaciones y conexiones solares, sin asumir conocimientos actuales ni acreditaciones PRL o carnés no confirmados.
- Las becas no son automáticamente adecuadas: comprobar si exigen matrícula o convenio de prácticas vigente.
- Cursos: repaso y progresión, online o presencial local, gratuitos/subvencionados prioritarios; hasta 800 € cuando el valor y el precio estén justificados. No confundir encaje con calidad docente.

## Organización propuesta para revisar

Mantener colores y cuatro pestañas superiores: VFX, Código, Electricidad, Cursos.

En empleo: buscador y botón Filtros; resumen discreto de filtros activos y número de resultados. Cada tarjeta muestra puesto, empresa, lugar/modalidad y un estado de encaje. Guardar mediante icono; descripción, evidencia, requisitos y acciones de candidatura dentro del detalle. Mantener visible un aviso crítico que impida presentar la oferta como compatible.

En cursos: especialidad y objetivo; tarjetas con título, proveedor, coste, modalidad y nivel. Programa, acceso, fechas, duración y explicación de recomendación en el detalle. Presentar el objetivo como una elección, sin asumir que el usuario solo necesita repasar.

En Radar: separar Estadísticas, Mapa y Fuentes. Estadísticas por especialidad; para cursos, distribución por proveedor, temática, objetivo/nivel, coste y modalidad. Mostrar por separado el catálogo total y los resultados tras filtros. Las fuentes con cero resultados siguen apareciendo sin inventar oportunidades.

## Cobertura comprobada en los datos locales

- Programación: Workable, Recruitee y SuccessFactors; también webs de empresa, portales remotos y SNE. Conectar un ATS no implica consultar todas sus empresas ni conseguir ofertas de entrada.
- Electricidad: SmartRecruiters mediante Veolia; fichas seleccionadas de Adecco y consultas SNE. Cobertura escasa: dos ofertas locales en este corte.
- Formación automática: eFundae 21, DIPLOS 16 y CNTG 1. Recursos fijos adicionales: dos de programación y tres VFX. Deben distinguirse en estadísticas.
- El último estado guardado contiene errores de ArtStation y ofertas privadas Xunta. Son estados del escaneo guardado, no una comprobación en vivo de hoy.
- APK 0.8.0: 204 ofertas adicionales y 38 cursos automáticos incluidos. Feed del repositorio: 207 ofertas tras añadir tres de Stratos. La actualización descargada puede cambiar el contenido mostrado; no confundir versión del APK con fecha del feed.

## Orden recomendado de trabajo

1. Ajustar el modelo de perfil y requisitos; probar grado obligatorio frente a FP alternativa, experiencia equivalente, requisitos desconocidos y becas.
2. Simplificar listado y fichas de las cuatro especialidades sin perder funciones de solicitudes ni filtros.
3. Añadir objetivos formativos y ampliar cobertura concreta VFX/videojuegos; verificar programa, precio y vigencia antes de recomendar cursos nuevos.
4. Normalizar procedencia y construir estadísticas por categoría, incluyendo fuentes fallidas y conectadas sin coincidencias.
5. Validar en pantallas estrechas, tamaño de texto ampliado, navegación al detalle y filtros persistidos; revisar después la APK en dispositivo.

Referencias de código: `mobile/lib/career_categories.dart`, `mobile/lib/main.dart`, `mobile/lib/insights.dart`, `scanner/mobile_careers.py`, `scanner/radar_sources.py`, `scanner/training_sources.py`.
