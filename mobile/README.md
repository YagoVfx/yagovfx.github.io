# Yago Job Radar — Android 0.11.0

## Novedades 0.11.0

- VFX reúne empresas y portales en una lista por identidad de vacante. Procedencia se convierte en filtro; se conservan filtros de país, UE, modalidad, contrato, fechas, condiciones y guardados.
- Código y Electricidad: municipios de Vigo y A Coruña, no sus provincias ni áreas metropolitanas. Programación mantiene remoto compatible desde España, incluido el ámbito internacional expresamente permitido. Los datos locales ambiguos de Inditex no se consideran prueba de municipio de A Coruña.
- Cursos de pago seleccionados y comprobados: tres de Coloso, con precio original USD, equivalencia EUR orientativa del BCE, fecha del cambio, nivel e idioma. No se presentan como precios finales ni valoraciones de calidad.
- Animum: ficha específica de Máster VFX y Composición con precio por consultar. Está fuera de los cursos con presupuesto confirmado; aparece al activar “Incluir precio por consultar”. El precio desconocido no se trata como gratuito ni como inferior a 800 €.
- Oposiciones: nueva categoría, por defecto solo municipios de Vigo y A Coruña. El catálogo público proviene de consultas de acceso libre y niveles FP del buscador oficial PAG. Se muestran plazas, titulación, plazo orientativo, referencia y enlaces oficiales, sin presentar solicitudes. Guardar interés es local.
- La convocatoria PAG 222569 incluye DAM y dos plazas de Técnico/a Superior de Informática de A Coruña. El anuncio BOE-A-2026-20340 está enlazado. El PAG informa fin de plazo 29/10/2026; deben confirmarse las bases y modificaciones.
- Las convocatorias provinciales o estatales no se incluyen en la vista municipal. Se pueden consultar cambiando el ámbito, con destino estatal por confirmar.
- El scanner actualiza `data/public-exams.json` junto con los demás datos. Cobertura parcial: el buscador PAG no recoge toda la contratación municipal ni todas las bolsas. Nunca se inventan plazas o fechas no publicadas.
- Feed móvil coverageVersion 6. APK local: `dist/yago-vfx-jobs-0.11.0.apk`.

## Novedades 0.10.0

- Jerarquía visual: títulos destacados, empresa en morado, información secundaria atenuada, verde para datos confirmados/acciones registradas y ámbar para requisitos por revisar. Los colores siempre llevan texto.
- Filtros en panel independiente; Cursos ocupa menos altura antes de las fichas. El objetivo se resume y se cambia dentro del panel. Se muestra la cantidad visible frente al catálogo de la especialidad.
- Se retiran las puntuaciones numéricas de encaje. FP mencionada, experiencia equivalente y prácticas se distinguen sin garantizar elegibilidad.
- Las copias VFX con URL original concreta compartida usan la identidad de la vacante de empresa. Se conservan IDs anteriores y procedencias para reconocer candidaturas históricas y guardados. No se borran registros privados antiguos ni se unen notas automáticamente.
- Web y Android buscan las candidaturas por identidad, alias y URL concreta antes de crear otro registro; se conservan sus fechas y notas. Las reglas de Firebase no cambian.
- Radar: Estadísticas / Mapa / Fuentes. Los totales VFX se unifican por identidad; las otras especialidades comparan catálogo y filtros guardados. Se mantiene la gráfica de ATS de empresas VFX.
- “De dónde sale” muestra origen, publicador, método, comprobación guardada y enlace original. Distingue selección fija de fichas con comprobación automática.
- Duraciones en horas/minutos y fechas legibles. El guardado local se explica una sola vez; las candidaturas siguen sincronizadas con la cuenta de la web.
- Feed compatible: coverageVersion 5. La APK incluye la copia actual y rechaza copias anteriores incompatibles hasta publicar el nuevo scanner.
- APK: `dist/yago-vfx-jobs-0.10.0.apk`. Los cambios están preparados para subir con GitHub Desktop; el APK no se versiona.

La unificación requiere el mismo enlace concreto: no infiere que dos anuncios con URLs diferentes sean la misma vacante ni agrupa páginas generales de empleo.

## Novedades 0.9.0

- Listados resumidos: título, empresa/proveedor, ubicación/coste y guardar. Pulsar una ficha abre requisitos y acciones de candidatura; los filtros se despliegan bajo demanda.
- Programación empieza en Entrada / FP; Por revisar y Todos se eligen desde Filtros. Electricidad oculta inicialmente experiencia alta y universidad expresamente obligatoria. Los requisitos desconocidos siguen identificados para revisión. “Engineer” por sí solo no excluye; FP o experiencia equivalente se distinguen de un grado obligatorio. Las prácticas requieren confirmar acceso.
- Perfil de referencia: DAM, electricidad/electrónica y telecomunicaciones; no se atribuye un grado universitario ni experiencia profesional de programación.
- Cursos: objetivos Repasar, Mejorar y Aprender algo nuevo cambian la prioridad; ya no se favorece siempre formación inicial. El criterio mide encaje, no calidad docente.
- Cuatro lecciones originales de SideFX se comprueban en cada escaneo: fluidos en tiempo real, destrucción, PCG y recursos para Unreal. Son autoaprendizaje, no certificaciones; algunas versiones y licencias de software tienen requisitos propios.
- Radar separa Especialidades, VFX directo y Mapa. Las estadísticas adicionales muestran ATS conectados incluso con cero ofertas, procedencia y experiencia; formación desglosa proveedor, temática, nivel, modalidad, coste y tipo de recurso. Las fuentes se filtran por categoría.
- Feed coverageVersion 4: incorpora metadatos de categorías y plataformas. La app conserva su copia compatible si el servidor todavía publica una versión anterior.
- APK local: `dist/yago-vfx-jobs-0.9.0.apk`. Los cambios del scanner y del feed necesitan publicarse mediante GitHub para actualizarse en línea.

Las cifras de versiones anteriores que figuran abajo documentan sus escaneos; no son recuentos en tiempo real.

App Flutter personal que consume `https://yagovfx.github.io/data/jobs.json`.
El scanner sigue ejecutándose en GitHub Actions. Firebase Authentication protege las candidaturas;
el APK solo incluye la configuración pública del cliente, nunca la contraseña del usuario.

El módulo VFX conserva sus fuentes ATS y webs oficiales. Adzuna y sus registros antiguos
quedan fuera. Programación incorpora además portales remotos, identificados como tales.
APK de prueba: `dist/yago-vfx-jobs-0.8.0.apk` (no versionada).

## Novedades 0.8.0

- VFX → **Estudios directos / Portales automáticos**. Hitmarker, Work With Indies y GamesJobsDirect
  ya importan fichas; no se mezclan con la verificación del scanner de estudios ni sus estadísticas.
  Hay filtro UE, remoto, publicación y enlace al empleador cuando lo publica el portal.
- Stratos también se consulta automáticamente mediante su RSS y listado de Trabajo. Se excluye
  Colaboración y se muestra el carácter freelance cuando consta. La APK 0.8.0 recibe la fuente
  al publicar y actualizar el feed; no necesita otra versión para mostrarla.
- Nuevos conectores de Indra/Minsait, Inditex/Zara (Recruitee) y mantenimiento eléctrico Veolia.
- Cursos → tres especialidades visibles, orden de encaje explicado, horas, fechas, requisitos y programa
  cuando constan en la fuente. No se inventan puntuaciones de calidad ni certificados.
- DIPLOS y CNTG automáticos: excluyen ubicaciones presenciales fuera de Vigo/Coruña y cursos/plazos cerrados.
- Bloqueos visibles: ArtStation HTTP 403 y ofertas privadas de Xunta HTTP 400. InfoJobs sigue aplazado.
- Diagnóstico detallado en `../FUENTES_RADAR.md`. La cobertura eléctrica sigue siendo reducida.

## Categorías adicionales, solo en Android

Las cuatro pestañas superiores son VFX, Código, Electricidad y Cursos, con los colores existentes. La web conserva su
buscador VFX. `scanner/mobile_careers.py` publica `data/mobile-careers.json` cada seis horas
en el mismo workflow; el APK incluye una copia inicial y conserva la última descarga válida.
Es necesario subir estos cambios a GitHub para activar las actualizaciones del nuevo feed.

- Programación: Vigo, A Coruña y remoto internacional. Se muestran todos los niveles por
  defecto, indicando experiencia; el interruptor permite ocultar los puestos avanzados.
  Remoto internacional no garantiza que el empleador contrate desde España: se revisan país, idioma y horario.
- Electricidad: Vigo y A Coruña; no acepta automáticamente desplazamientos. Los requisitos
  PRL, viajes y experiencia aparecen para revisar en la ficha y en su fuente original.
- Cursos: online o presenciales en Vigo/A Coruña, prioridad a gratuitos y precio confirmado de hasta
  800 €. Los niveles avanzados son opcionales. Se distingue un curso de una guía técnica.
- Las candidaturas se guardan con el mismo contrato privado de Firestore que VFX y aparecen
  también en Solicitudes de la web. No requiere modificar de nuevo las reglas publicadas.
  Las guardadas y el progreso de formación son locales; no se presentan como sincronizados.
- Filtros de publicación: últimas 24 horas, semana o mes. Fechas desconocidas quedan fuera
  al activarlos; la fecha de comprobación nunca se usa para aparentar que un anuncio es nuevo.
- Candidaturas: vistas Todas / En seguimiento / Cerradas y filtro por fecha de envío.
  Retirada y Rechazada conservan historial; Eliminar borra el registro privado de ambos dispositivos
  tras confirmación, sin retirar el CV enviado. No se borran automáticamente por antigüedad.

Fuentes automáticas: SNE (servicio público de empleo, no ATS), Workable de Plain Concepts,
Fabulous y EUROPEAN DYNAMICS, Imatia/Inprosec, RSS de We Work Remotely, API Remote OK,
algunas fichas originales seleccionadas de Adecco, Indra, Inditex, Veolia, portales VFX (Hitmarker,
Work With Indies, GamesJobsDirect) y cursos eFundae/DIPLOS/CNTG. Los portales todavía no conectados
se muestran como enlaces manuales, sin contabilizarlos como ofertas. Emprego Galicia devuelve un error en su formulario
al automatizar la consulta. La cobertura es parcial, no una búsqueda exhaustiva de Internet.
Si una fuente falla, se conserva su copia anterior con aviso y sin actualizar su fecha de revisión.

La consulta ampliada del 24/10/2026 encontró 23 ofertas de programación/soporte,
dos eléctricas locales, 179 anuncios VFX complementarios y 38 cursos automáticos. Se incluyen además
dos recursos de programación y tres de VFX seleccionados. Los recuentos visibles dependen de los filtros.
El feed móvil usa schemaVersion 2 y coverageVersion 3: evita reemplazar la copia ampliada del APK por datos de la versión anterior
mientras se publican los cambios. Las versiones antiguas conservan su última copia compatible.

## Incluido

- Filtro Unión Europea: los 27 países, ciudades reconocidas y ámbito UE explícito. No confunde
  Europa genérica, Reino Unido, Noruega o Suiza con la UE; no acredita permiso de trabajo.
- Solicitudes: misma cuenta Firebase que la web, estados Enviada / Entrevista / Oferta recibida /
  Rechazada / Retirada, notas privadas, fecha de envío y registro manual de candidaturas anteriores.
  Se sincronizan mediante Firestore cada 15 segundos y al abrir la pantalla o actualizarla.
  La sesión y la copia privada se cifran con Android Keystore; no se almacena la contraseña.
  Un fallo de escritura no marca una solicitud como guardada. Sin sesión se pueden consultar ofertas.
- Pestaña Radar: mapamundi con grupos pulsables, zoom por pellizco, doble toque y arrastre.
  Los grupos abren nombres legibles; seleccionar una empresa enfoca sus ubicaciones y
  muestra sus fuentes. Se evita dibujar etiquetas superpuestas. Hexworks comparte CI Games.
- Enlace visible a Jobs VFX Scanner en GitHub desde Radar.
- Los puntos verdes abren la ubicación pulsada sin mover la cámara. El botón
  «Ver todas sus sedes» enfoca todas las ubicaciones de la empresa de forma explícita.
- Gráfica circular de ofertas VFX activas por plataforma, ranking, cantidades y porcentajes;
  incluye plataformas con cero ofertas y las coincidencias posibles, sin filtros personales.
- Cartografía Natural Earth de dominio público incluida localmente. Ubicaciones y catálogo
  se actualizan desde la misma web; se incluye una copia inicial y caché para usar sin conexión.
- Búsqueda por palabras, sin distinguir acentos; vistas Todas / Compatibles / Para revisar.
- España, modalidad, elegibilidad, contrato, verificación, coincidencias posibles y ordenación.
- Detalle con evidencia, origen, relevancia y apertura de enlaces http/https en navegador externo.
- Guardadas, descartadas y filtros persistentes en el teléfono; restauración de descartadas.
- Caché local, refresco manual y al abrir, ETag y aviso de datos antiguos (>13 horas).
- Compatibilidad con registros antiguos; formatos posteriores a schemaVersion 2 se rechazan con aviso.

Guardadas, descartadas y filtros son locales. La sincronización entre dispositivos cubre candidaturas.
No incluye todavía notificaciones ni recordatorios automáticos.
Las guardadas siguen los filtros de búsqueda/modalidad/contrato, pero permiten fuentes sin verificar.
Las ofertas cerradas nunca aparecen, tampoco en guardadas.

## Desarrollo

Desde `mobile/`:

```sh
flutter pub get
flutter analyze
flutter test
flutter run
flutter build apk --release
```

APK universal: `build/app/outputs/flutter-apk/app-release.apk`.
La compilación de prueba usa la firma de desarrollo local de Android, incluso en modo release;
no está preparada para publicar en Google Play. Las actualizaciones deben usar la misma firma.
La primera descarga requiere internet; después queda una copia local disponible sin conexión.

## Verificación

Los tests usan el fixture de la web y comprueban los mismos conjuntos de IDs para el filtro por
defecto, España, elegibilidad, búsqueda, compatibles, revisión y guardadas. También verifican
la migración de Adzuna, enlaces inseguros, caché, versión del formato y arranque de widgets.

El proyecto se mantiene dentro de `mobile/`; consume los datos publicados por el scanner.
No subir `build/`, `.dart_tool/`, `android/local.properties` ni claves de firma a Git.
