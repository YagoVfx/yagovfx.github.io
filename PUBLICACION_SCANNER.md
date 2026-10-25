# Publicación del scanner

El workflow ejecuta `scripts/publish_scanner.py`. El publicador consulta la última revisión de `main` y crea un checkout temporal aislado; ahí instala las dependencias de esa revisión, ejecuta las pruebas y genera los siete archivos públicos de datos, incluidas las oposiciones.

Solo publica esos archivos mediante un push normal. Si alguien cambia `main` durante el escaneo, vuelve a generar usando la nueva revisión, hasta tres intentos. No hace force push ni resuelve conflictos de JSON eligiendo versiones antiguas. Los fallos del scanner o de las pruebas impiden publicar datos parciales.

El script está reservado a GitHub Actions. No modifica los archivos de trabajo del checkout original; elimina únicamente el worktree temporal creado para cada intento. La concurrencia del workflow sigue evitando que se ejecuten dos scanners simultáneos, y los reintentos cubren los pushes de usuarios.

Para activar una corrección del workflow hay que subirla primero a `main`. Después, iniciar una ejecución nueva desde Actions → VFX Jobs Scanner → Run workflow, seleccionando `main`. Repetir una ejecución antigua puede reutilizar la versión antigua del workflow.

Las actualizaciones automáticas de datos siguen siendo commits normales: GitHub Desktop puede necesitar un pull si el bot ha publicado desde el último pull local.
