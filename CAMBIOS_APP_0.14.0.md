# Rediseño visual de la app 0.14.0

Se mantiene la base oscura y se reorganiza la navegación y la jerarquía de las pantallas principales.

## Navegación

La barra inferior tiene tres destinos: Explorar, Guardadas y Solicitudes. Radar y Ajustes pasan a la cabecera, con retorno explícito a Explorar. Las categorías superiores tienen nombres completos, texto más legible y desplazamiento horizontal; la categoría seleccionada se coloca a la vista sin mover verticalmente la cabecera.

Los filtros continúan en una hoja independiente. El número de resultados gana protagonismo y se separa del total del catálogo. Las explicaciones de cobertura y los enlaces externos permanecen al final de la lista.

## Jerarquía y colores

Las cabeceras distinguen VFX en violeta, programación en azul, electricidad en dorado, formación en verde agua y oposiciones en rosa. El color identifica el área, no garantiza compatibilidad ni vigencia.

Las tarjetas destacan primero el puesto o curso, después la empresa o centro y finalmente modalidad y datos secundarios. Una acción de texto indica que se puede abrir el programa o los requisitos. Los cursos destacan su precio: verde para gratuito/subvencionado, azul para importe conocido y ámbar cuando falta confirmarlo.

Los estados conservan etiquetas además de color. Las candidaturas usan violeta para enviada, azul para entrevista, verde para oferta recibida, rosa para rechazada y gris para retirada. La información pendiente de comprobar usa ámbar. Las convocatorias cuyo plazo publicado termina en siete días o menos muestran un aviso para confirmarlo en las bases; una ficha retenida no se presenta como comprobada recientemente.

Las pantallas sin resultados ofrecen una explicación corta y una acción para revisar filtros. Candidaturas y Ajustes comparten la nueva presentación. Se retira el error técnico crudo del resumen de actualización de Ajustes.

## Validación

40 pruebas Flutter superadas y análisis sin incidencias. Las pruebas recorren navegación, filtros, apertura de formación y candidaturas, e incluyen pantallas de 320 píxeles de ancho.

Se han generado y revisado siete capturas de widgets reales a 390 × 844: VFX, programación, electricidad, cursos, oposiciones, acceso a candidaturas y ajustes. Se usan fuentes legibles equivalentes a las del sistema, porque los tests de Flutter no cargan las fuentes de producción por defecto. Las capturas muestran el estado de consulta sin red propio del entorno de pruebas. No son fotografías de un teléfono físico. Artefactos locales ignorados en `.venv/visual-014/`.

APK local: `mobile/dist/yago-vfx-jobs-0.14.0.apk`. No se suben instaladores, ZIP ni capturas de pruebas a Git. Esta versión incluye también las correcciones de fuentes y cursos preparadas en la 0.13.0; hay que publicar el código y los datos pendientes juntos.
