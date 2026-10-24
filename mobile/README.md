# Yago VFX Jobs — Android 0.6.0

App Flutter personal que consume `https://yagovfx.github.io/data/jobs.json`.
El scanner sigue ejecutándose en GitHub Actions. Firebase Authentication protege las candidaturas;
el APK solo incluye la configuración pública del cliente, nunca la contraseña del usuario.

Desde 0.2.0 solo admite fuentes ATS y webs oficiales. Adzuna, sus señales y los registros
antiguos de agregadores quedan fuera, también en caché y guardadas.
APK de prueba: `dist/yago-vfx-jobs-0.6.0.apk` (no versionada).

## Categorías adicionales, solo en Android

El selector de categoría añade Programación, Electricidad y Cursos. La web conserva su
buscador VFX. `scanner/mobile_careers.py` publica `data/mobile-careers.json` cada seis horas
en el mismo workflow; el APK incluye una copia inicial y conserva la última descarga válida.
Es necesario subir estos cambios a GitHub para activar las actualizaciones del nuevo feed.

- Programación: Vigo o teletrabajo desde España, prioridad junior y repaso. Los puestos
  con experiencia alta se ocultan inicialmente y se pueden incluir con el interruptor.
- Electricidad: localidad Vigo; no acepta automáticamente desplazamientos. Los requisitos
  PRL, viajes y experiencia aparecen para revisar en la ficha y en su fuente original.
- Cursos: online o presenciales en Vigo, gratuitos primero y precio confirmado de hasta
  800 €. Los niveles avanzados son opcionales. Se distingue un curso de una guía técnica.
- Las candidaturas se guardan con el mismo contrato privado de Firestore que VFX y aparecen
  también en Solicitudes de la web. No requiere modificar de nuevo las reglas publicadas.
  Las guardadas y el progreso de formación son locales; no se presentan como sincronizados.

Fuentes automáticas: SNE (servicio público de empleo, no ATS), Workable de Plain Concepts,
Fabulous y EUROPEAN DYNAMICS, y cursos eFundae. Los demás portales se muestran como enlaces
manuales, sin contabilizarlos como ofertas. Emprego Galicia devuelve un error en su formulario
al automatizar la consulta. La cobertura es parcial, no una búsqueda exhaustiva de Internet.
Si una fuente falla, se conserva su copia anterior con aviso y sin actualizar su fecha de revisión.

La consulta inicial del 24/10/2026 encontró dos ofertas de programación con experiencia alta,
ninguna oferta eléctrica en Vigo en estas fuentes y 21 cursos eFundae. Se incluyen además
una ruta inicial de C# y una guía Java oficiales. Los recuentos visibles dependen de los filtros.

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
