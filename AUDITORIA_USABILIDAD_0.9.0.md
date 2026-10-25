# Auditoría visual, comprensión y procedencia — app 0.9.0

Fecha: 25/10/2026. Revisión posterior a la reorganización y al merge del scanner.

## Alcance y conclusión

Se han renderizado e inspeccionado nueve estados de la interfaz Flutter a 390 × 844: VFX directo, programación, electricidad, cursos VFX, filtros de cursos, detalle de formación, estadísticas, ajustes y acceso a solicitudes. Se usaron datos locales y una fuente de texto equivalente para hacer legibles las capturas. No es una sesión en un teléfono Android: pueden variar fuentes, barras del sistema y teclado. Las capturas de listas ocultan el fallo de red simulado por el entorno de pruebas para examinar su estado normal. El error de recuperación de sesión de la captura de acceso también pertenece al entorno de pruebas; no se considera un fallo de producción.

Se contrastaron etiquetas, filtros y estadísticas con su implementación y los JSON del repositorio. Los estados de fuentes citados son del último escaneo guardado, no comprobaciones HTTP en vivo de esta auditoría. No se inició sesión ni se modificaron candidaturas privadas.

**La app ha mejorado al resumir las tarjetas, pero todavía exige conocer cómo está construida para interpretar algunos resultados.** El principal trabajo pendiente es dar un significado consistente a recuentos, recomendaciones y fuentes, además de reducir la altura de los controles en Cursos.

## Problemas prioritarios comprobados

| Prioridad | Lo que puede entender el usuario | Lo que ocurre realmente | Corrección recomendada |
|---|---|---|---|
| Alta | «Ya he marcado esta oferta, debería estar marcada en todas partes». | Hay 28 anuncios complementarios VFX cuyo enlace de vacante coincide con una oferta activa del scanner directo, con identificadores diferentes. Las candidaturas se guardan por ID. | Identidad común de vacante, conservando todas sus procedencias; sincronizar guardado/candidatura entre copias. No sumar anuncios como oportunidades únicas. |
| Alta | «100/100 de encaje» significa que este curso es perfecto para mí. | Es una suma de reglas: gratuidad, nivel inicial, título, duración, etc. El curso introductorio de Houdini alcanza 100 sin medir conocimientos actuales, calidad docente ni resultados. | Quitar la puntuación numérica de cara al usuario. Mostrar objetivo y motivos concretos: “Fundamentos”, “Proyecto práctico”, “Necesita base en Houdini”. |
| Alta | «Entrada / FP» significa que cumplo los requisitos. | La vista inicial incluye junior y becas aunque sus requisitos estén sin confirmar; esto se ve en las tarjetas SAP. Una alternativa de experiencia a un grado tampoco acredita que el usuario tenga esa experiencia. | “Para empezar” y una etiqueta separada de acceso: FP explícita, experiencia equivalente o acceso por confirmar. Prácticas: confirmar matrícula/convenio. Evitar mezclar estas tres evidencias. |
| Alta | «Tengo 23 ofertas disponibles» en estadísticas debería coincidir con mi lista. | La captura de programación muestra 4 en la vista inicial y 23 en estadísticas sin filtros. En electricidad se ven 1 de las 2 importadas por el filtro inicial de experiencia. | Mostrar “23 encontradas · 4 en tu vista” y permitir ver/limpiar filtros desde ese resumen. Aclarar catálogo frente a selección personal. |
| Alta | «Compatible» y «Verificada» son garantías de adecuación y vigencia. | La compatibilidad VFX considera condiciones de la oferta y elegibilidad; no demuestra encaje completo de experiencia/titulación. Verificación no equivale a confirmación humana de contratación. | Etiquetas más concretas: “Cumple filtros de búsqueda”, “Procedencia oficial”, “Última comprobación…”. Explicar por separado lo que sigue sin confirmar. |
| Media | «Automático» significa que se descubren cursos nuevos continuamente. | SideFX consulta cuatro páginas concretas seleccionadas; Adecco comprueba unas fichas seleccionadas. Esto difiere de descubrir resultados en un catálogo o búsqueda. | Distinguir “Búsqueda automática”, “Ficha seleccionada con revisión automática” y “Enlace para buscar tú”. |
| Media | Las estadísticas muestran cursos que puedo elegir ahora. | Los gráficos de formación cuentan el catálogo sin aplicar presupuesto, especialidad, modalidad ni vencimientos del listado. | Mostrar total recopilado y disponible tras filtros/plazos, con denominador explícito. |
| Media | «Proveedor» identifica siempre quién imparte un curso. | El desglose usa `source` si existe y `provider` si no: mezcla plataforma de origen e impartidor. | Dos conceptos: “Dónde lo encontramos” y “Quién lo imparte”; informar si el segundo no está confirmado. |
| Media | Una fuente marcada como correcta ha producido ofertas. | Unas fuentes publican examinadas y otras importadas; cero coincidencias no significa consulta fallida. Los nombres mezclan empresa y ATS. | Por fuente: estado, fecha de consulta, empresas consultadas, fichas revisadas y anuncios importados en columnas distintas. |

La coincidencia de las 28 URLs se comprobó preservando los parámetros de identificación y retirando solo parámetros de seguimiento habituales. Ejemplos: VFX Intern de Respawn y puestos VFX de Riot Games. Hay que revisar también duplicación entre portales antes de definir el total único definitivo.

## Recorrido visual por pantallas

### Entrada y navegación

El contraste oscuro/morado y la selección de pestañas son claros. El título “YAGO / VFX JOBS” se queda corto para una app con programación, electricidad y formación. “Código” arriba y “Programación” dentro de la pantalla añaden una pequeña inconsistencia. La pestaña inferior “Ofertas” también contiene cursos.

Propuesta: mantener el estilo, usar un nombre general y una terminología estable. La navegación debe responder a “buscar”, “guardar”, “seguir mis candidaturas” y “ver cobertura”, sin que el usuario tenga que entender módulos internos.

### VFX

La primera tarjeta aparece aproximadamente a los 370 píxeles. Hay dos niveles de selección superiores y tres vistas debajo del buscador. El diseño de las tarjetas VFX difiere del de programación/electricidad: jerarquía, chips y tamaño.

“Estudios directos” y “Portales automáticos” pueden interpretarse como búsqueda manual frente a automática, aunque ambas son automáticas. Además, separar las dos listas hace menos visible la duplicación.

Propuesta: una lista común de vacantes únicas con filtro de procedencia “Empresas” / “Portales”, y una indicación discreta “Encontrada en 2 fuentes”. Si se mantiene la separación, explicar que ambas se actualizan automáticamente y compartir el estado de candidatura.

### Programación y electricidad

La lista es más fácil de explorar que antes y el botón de guardar es reconocible. Sin embargo, las tarjetas no muestran claramente modalidad, fecha ni procedencia. En programación aparece “Requisitos por confirmar” dentro de una vista titulada “Entrada / FP”. En electricidad el contador “1 ofertas” da sensación de poco cuidado y no explica que hay otro anuncio oculto por filtros.

Propuesta de tarjeta: puesto; empresa y lugar; modalidad y antigüedad; una única etiqueta de acceso relevante. La fuente debe estar a un toque y no competir visualmente con el título. Los filtros activos deben poder reconocerse estando cerrados, con un botón de restablecer.

El buscador tiene el mismo texto largo en todas las especialidades. “Buscar puesto o empresa” y “Buscar curso o herramienta” serían más directos.

### Cursos

La primera ficha empieza aproximadamente a los 495 píxeles: especialidad, salto de línea de las opciones, objetivo, buscador, filtros y contador ocupan gran parte de la pantalla. Al abrir filtros, la lista empieza aproximadamente a los 725 píxeles. La separación por especialidad funciona, pero el usuario pierde de vista el contenido al configurar.

Las tarjetas dicen proveedor, gratuidad y `online`, pero omiten qué se aprende, nivel y duración. El detalle es limpio, aunque muestra una duración decimal (“1.14 horas”) y da más protagonismo al encaje numérico que al resultado del aprendizaje. La unidad original debe validarse antes de convertirla a horas/minutos.

Propuesta: especialidad compacta; objetivo dentro del mismo panel de filtros; resumen visible como “VFX · Mejorar · Online”. Cada tarjeta debería responder “qué aprenderé”, “qué necesito saber antes”, “cuánto dura” y “cuánto cuesta”. Sustituir los decimales por una duración legible y separar tutorial, guía y curso desde el listado.

### Radar y estadísticas

La separación del mapa es positiva. Sin embargo, “Especialidades / VFX directo / Mapa” mezcla dos criterios: categorías y visualizaciones. Hay que entrar en “Especialidades” para descubrir que allí están las estadísticas de programación y cursos. Los ATS de programación suman 8 anuncios, frente al total de 23; el resto procede de webs y portales, pero la relación no se presenta de forma inmediata.

Propuesta: “Estadísticas / Mapa / Fuentes”. Dentro de Estadísticas elegir especialidad, y dentro de VFX elegir total único o procedencia. Mostrar dos o tres cifras principales; desplegar los desgloses después. Fechas en formato “25 oct., 06:27”, con zona horaria, en lugar de una cadena ISO con fracciones y `Z`.

### Ajustes y solicitudes

Ajustes es principalmente un bloque explicativo. “Ofertas cargadas: 86” no representa lo que se ve en el listado y solo corresponde al módulo VFX. “Actualizar ahora” actualiza ese módulo, aunque el usuario esté pensando en toda la app. Se repite la explicación de guardados y sincronización.

El acceso a Solicitudes es sencillo, pero “email y contraseña de Firebase” obliga al usuario a conocer infraestructura. Debería decir “La misma cuenta que usas en la web”. Guardadas y candidaturas tienen comportamientos distintos: solo las segundas se sincronizan. Esa diferencia debe explicarse al guardar por primera vez, sin repetirla continuamente.

No se evaluó visualmente el contenido privado de una cuenta iniciada; la revisión de estados, fechas y borrado de candidaturas en esta auditoría es de código.

## De dónde sale cada cosa

| Contenido | Origen y método actual | Lo que conviene explicar |
|---|---|---|
| VFX de empresas | `data/jobs.json`: scanner de empresas concretas mediante ATS y webs originales. | Se consultan empresas configuradas, no todas las empresas de cada ATS. |
| VFX de portales | `data/mobile-careers.json`: Hitmarker, GamesJobsDirect, Work With Indies y Stratos. | Son anuncios de portales; algunos enlazan a vacantes ya presentes en empresas. No sumar sin deduplicar. |
| Programación | Workable de empresas configuradas, Recruitee de Inditex, SuccessFactors de Indra/Minsait, Imatia/Inprosec y portales remotos. SNE aporta consultas públicas. | ATS, empleador y portal son conceptos diferentes. El remoto debe permitir contratación desde España. |
| Electricidad | Veolia mediante SmartRecruiters, fichas seleccionadas de Adecco y consultas SNE. | Cobertura parcial y muy pequeña; no representa todo el empleo local. Adecco no es una búsqueda exhaustiva de su catálogo. |
| Cursos públicos | eFundae, DIPLOS y CNTG. | Catálogo, inscripción abierta y plaza disponible no son lo mismo. |
| Formación VFX nueva | Cuatro lecciones de SideFX seleccionadas y comprobadas automáticamente. | No se descubre todo el catálogo SideFX. Son tutoriales de autoaprendizaje; acceso gratuito no incluye necesariamente licencias de software. |
| Recursos seleccionados | `career-resources.json`: dos recursos de programación y tres de VFX. | Es una selección fija incluida en la app, con fecha de revisión propia. |
| Directorio de enlaces | Páginas generales y búsquedas que abre el usuario. | No son ofertas importadas ni cursos confirmados. “Fuentes y buscadores oficiales” puede confundirse con fuentes gubernamentales o del empleador. |

En el corte del repositorio: 181 anuncios VFX complementarios, 23 de programación y 2 eléctricos. Formación: 42 recursos del feed más 5 seleccionados, distribuidos en 29 de programación, 11 de electricidad y 7 de VFX. Son recuentos de catálogo, no de compatibilidad ni de oportunidades únicas.

La copia inicial de la APK contiene 207 anuncios adicionales, frente a 206 del JSON del repositorio tras el scanner. Esto es normal al actualizarse los datos sin reinstalar: falta presentar claramente “versión de app” y “última actualización de cada fuente”.

En el último estado guardado figuran errores en ArtStation, ofertas privadas de Xunta, DIPLOS y CNTG. En formación se conservan fichas anteriores cuando falla una consulta. Es preferible mostrar “Última comprobación correcta…” y un aviso concreto a un error HTTP largo. Un fallo de DIPLOS no significa que también falle el resto de cursos de Xunta o SNE.

## Orden de retoque recomendado

1. Unificar identidad y candidatura de las vacantes duplicadas; fijar la definición de los totales.
2. Corregir el lenguaje de compatibilidad, FP, procedencia y recomendación de cursos. Retirar la puntuación 100/100.
3. Mostrar filtros activos y reducir la cabecera de Cursos; unificar tarjetas y formato de fechas/duración.
4. Reorganizar Radar en Estadísticas / Mapa / Fuentes y hacer visible catálogo frente a selección personal.
5. Añadir una ficha de procedencia por elemento: encontrado en, publicado por, método de recogida, última comprobación correcta y enlace original.
6. Simplificar Ajustes y el texto de acceso, y explicar una sola vez qué se sincroniza.

## Evidencia local y límites

Capturas de inspección guardadas en `.venv/audit-09/`: `vfx.png`, `programming.png`, `electricity.png`, `courses.png`, `courses-filters.png`, `course-detail.png`, `statistics.png`, `Ajustes.png`, `Solicitudes.png`. Son artefactos locales, no versionados. El render de inspección pasó sin excepciones de diseño en esa resolución. Esto no sustituye una revisión en Android con teclado, texto ampliado, lector de pantalla y uso real de la cuenta.

Código contrastado: `mobile/lib/main.dart`, `career_categories.dart`, `profile_fit.dart`, `career_statistics.dart`, `insights.dart`, `jobs.dart`, `applications.dart`; metadatos de `scanner/career_metadata.py` y catálogos JSON.
