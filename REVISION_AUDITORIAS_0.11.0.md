# Revisión conjunta de las auditorías de Yago Job Radar 0.11.0

Fecha: 26 de octubre de 2026.

Las dos partes aportan hallazgos útiles. El problema principal es la fiabilidad de la selección que ve el usuario: algunas ofertas incompatibles entran y otras válidas quedan ocultas. La ampliación de fuentes debería venir después de corregir esa selección y la información sobre vigencia.

Esta revisión contrasta el texto aportado y el Word de la segunda parte con el código y los datos locales. No modifica el producto ni publica datos. No ejecuta la APK ni consulta las fuentes externas en directo. Los recuentos describen el archivo local, no la cobertura actual de Internet.

## Problemas confirmados

| Prioridad | Problema | Comprobación y consecuencia |
| --- | --- | --- |
| Alta | Experiencia mal clasificada | Ejecutar `classify_offer` con «Persona responsable. Experiencia de 1 año» devuelve `experienced`. La palabra responsable basta. Puede ocultar un puesto eléctrico adecuado. |
| Alta | Remoto incompatible con España | Ejecutar `permitted_remote` con región mundial y «Remote - US», «Remote U.S.» o «Remote from the US» devuelve verdadero. En cambio sí rechaza «must be based in United States». La protección existe, pero es incompleta. WWR impone después `workplace=remote`, sin conservar una clasificación híbrida del texto. |
| Alta | Frescura del feed equívoca | `mobile_careers.run` escribe `updatedAt=now` incluso cuando fallan los lectores y conserva registros anteriores. Eso acredita un intento, no una actualización correcta de las ofertas. Los registros sí conservan su `checkedAt`; hace falta usarlo y explicarlo mejor. |
| Alta | Cursos retenidos sin caducidad suficiente | Las ramas de retención de cursos no comprueban sus fechas. En el cliente la comprobación usa fin de inscripción o fin del curso, no el inicio. No debe asumirse que cualquier curso empezado admite todavía matrícula. |
| Alta | Requisitos académicos poco reconocidos | `profile_fit.dart` exige unas pocas expresiones para detectar universidad y no reconoce todas las formulaciones de FP. «Formación universitaria» y «Grado medio/superior» quedan insuficientemente cubiertos. Hay que distinguir obligación, preferencia y alternativa por experiencia. |
| Alta | Municipios con falsos negativos | Ejecución real: «Teis, Vigo», «Bouzas (Vigo)», «Zona Franca, Vigo» y «Coruña, A» quedan fuera. «Arteixo, A Coruña» queda fuera correctamente. Deben incorporarse alias y barrios sin ampliar el ámbito a toda la provincia. |
| Alta | Identidad de candidaturas diferente en web | La expresión regular de `key()` considera genérica cualquier ruta terminada en barra. Reproducido con `/company/j/C698FE1D89/`. La coincidencia por ID sigue funcionando, pero falla la recuperación alternativa por URL. |
| Media | Duplicados por URL diferente | `vacancy_identity.py` normaliza URL y parámetros de seguimiento; no extrae identificadores de cada ATS. Por eso no puede unir de forma general variantes con sufijos o dominios distintos. No se ha validado aquí individualmente cada grupo propuesto por Claude. |
| Media | Radar en Oposiciones muestra otra categoría | `main.dart` cambia explícitamente `public` a `programming` al abrir Radar. Es una sustitución confusa. |
| Media | Diagnóstico de sincronización demasiado específico | La web interpreta cualquier 403 como reglas pendientes de publicar. Ese código también puede corresponder a otros problemas de permisos o validación. |
| Media | Consultas móviles en segundo plano | El temporizador de candidaturas se ejecuta cada 15 segundos sin comprobar el ciclo de vida de la app. Conviene detenerlo al pasar a segundo plano y actualizar al volver. |

## Datos y cobertura

El archivo local contiene 203 ofertas complementarias: 181 VFX, 20 de programación y 2 de electricidad; además, 46 cursos automáticos. Hay 17 cursos retenidos tras errores. Son coherentes con los recuentos de las auditorías, pero no prueban que las vacantes sigan abiertas hoy.

Los cuatro errores registrados son ArtStation, ofertas privadas de Xunta, DIPLOS y CNTG. El archivo demuestra fallos de esas consultas en esa ejecución. No demuestra que fallen siempre, que exista un bloqueo permanente de GitHub Actions ni que la causa de todos ellos sea la misma. Un timeout no equivale a prohibición de acceso.

Adecco revisa tres URLs seleccionadas: sirve para comprobar esas fichas, pero no para descubrir automáticamente todas las vacantes nuevas. La poca cobertura eléctrica está confirmada en el feed; que SNE esté omitiendo resultados por un cambio de formulario requiere comparar una búsqueda real con su respuesta al scanner.

El PAG envía parámetros de búsqueda y evita páginas repetidas. Que varias consultas tengan el mismo total es una señal para investigar, no prueba suficiente de que ignore los filtros. Debe comprobarse con consultas de control y resultados oficiales diferentes.

## Matices y correcciones a las auditorías

- La segunda parte corrige expresamente la sospecha inicial sobre SNE: su causa queda sin resolver. No debe trasladarse como fallo demostrado del servicio.
- Una OEP anuncia plazas previstas; una convocatoria abre un procedimiento con bases y plazos. No deben mezclarse en la lista de solicitudes abiertas.
- El ámbito solicitado es solo los municipios de Vigo y A Coruña. Añadir Xunta, diputaciones o universidades requiere comprobar destino y ámbito, o plantear una ampliación explícita del filtro. Su ausencia no es por sí sola un incumplimiento del alcance actual.
- No conviene fusionar anuncios solo por empresa, título y ciudad: pueden ser requisiciones diferentes. Usar ID del ATS y conservar alias anteriores protege las candidaturas existentes.
- Caducar por inicio no debe ser una regla universal: hay formación continua y matrícula abierta. La regla debe considerar inscripción, modalidad y evidencia de acceso, y mostrar incertidumbre cuando falten fechas.
- No ocultar experiencia por defecto en electricidad tiene sentido para este perfil. Eso no convierte automáticamente cualquier puesto senior en adecuado: deben mostrarse años y requisitos concretos.
- La presencia de una cadena en el APK no demuestra que una pantalla accesible la muestre. El texto corrupto debe limpiarse, pero su impacto visual necesita ejecutar esa ruta.
- La firma debug es una limitación de distribución conocida. Hace falta custodiar la clave actual para mantener actualizaciones de esta instalación; una migración a firma de distribución debe planificarse.
- Que el scanner móvil escriba alias en `jobs.json` es un acoplamiento real y deliberado para compartir identidad entre web y móvil. Debe documentarse y verificarse, no eliminarse sin sustituir esa función.
- Los horarios de Actions pueden retrasarse respecto al cron. Diferencias de cinco a siete horas no prueban un fallo del scanner.

## Orden de corrección propuesto

1. Corregir remoto, experiencia, requisitos académicos y alias municipales con casos reales y pruebas de regresión. Conservar separados los criterios de entrada para programación y electricidad.
2. Separar última ejecución de última consulta correcta; avisar de datos retenidos en las listas y revisar caducidad e inscripción de cursos y oposiciones.
3. Arreglar la normalización web de candidaturas y añadir identidad por ATS sin perder IDs, notas ni estados previos.
4. Comprobar SNE y PAG contra búsquedas oficiales, y mejorar descubrimiento eléctrico. Tratar cada fuente fallida según su causa comprobada.
5. Simplificar navegación y filtros, corregir Radar en Oposiciones y mostrar contrato, experiencia y procedencia donde ayuden a decidir.
6. Afinar clasificación y selección de cursos: especialidad real, repaso frente a mejora, requisitos de acceso, familias o itinerarios repetidos y precio confirmado.

## Verificación realizada

Se han ejecutado las funciones reales de clasificación y remoto con los casos descritos, y la expresión regular JavaScript con una URL de Workable. Pasan 9 pruebas existentes de identidad de vacantes, publicación concurrente y oposiciones. Esas pruebas no cubren todos los problemas anteriores: que pasen no invalida los hallazgos.

La segunda auditoría declara no haber ejecutado Flutter, la web ni las reglas de Firestore. Sus observaciones visuales son principalmente lectura de código. No hay base para afirmar una auditoría visual completa del comportamiento en un teléfono.
