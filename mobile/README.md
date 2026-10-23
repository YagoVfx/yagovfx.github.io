# Yago VFX Jobs — Android 0.2.0

App Flutter personal que consume `https://yagovfx.github.io/data/jobs.json`.
El scanner sigue ejecutándose en GitHub Actions; la app no contiene credenciales de Firebase ni Adzuna.

Desde 0.2.0 solo admite fuentes ATS y webs oficiales. Adzuna, sus señales y los registros
antiguos de agregadores quedan fuera, también en caché y guardadas.
APK de prueba: `dist/yago-vfx-jobs-0.2.0.apk` (no versionada).

## Incluido

- Búsqueda por palabras, sin distinguir acentos; vistas Todas / Compatibles / Para revisar.
- España, modalidad, elegibilidad, contrato, verificación, coincidencias posibles y ordenación.
- Detalle con evidencia, origen, relevancia y apertura de enlaces http/https en navegador externo.
- Guardadas, descartadas y filtros persistentes en el teléfono; restauración de descartadas.
- Caché local, refresco manual y al abrir, ETag y aviso de datos antiguos (>13 horas).
- Compatibilidad con registros antiguos; formatos posteriores a schemaVersion 2 se rechazan con aviso.

No incluye todavía notificaciones, pantalla de empresas, candidaturas ni sincronización entre dispositivos.
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

El proyecto se mantiene dentro de `mobile/`; no modifica el portfolio ni el scanner.
No subir `build/`, `.dart_tool/`, `android/local.properties` ni claves de firma a Git.
