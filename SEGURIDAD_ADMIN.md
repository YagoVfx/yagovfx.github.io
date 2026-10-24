# Seguridad del login de administrador

## Candidaturas privadas (24-10-2026)

Las candidaturas usan una colección separada: `users/{uid}/applications/{jobId}`.
Sus reglas permiten leer y escribir únicamente al UID administrador y validan los
campos y estados; nunca se incluyen en `portfolio/main`, los JSON públicos ni Git.
Las notas y la fecha se sincronizan entre web y Android con Firebase Authentication.
El móvil guarda la sesión y su caché privada cifradas con Android Keystore, sin guardar
la contraseña, y desactiva copias Android automáticas de esos datos. Al cerrar sesión
se borra la sesión y desaparecen las candidaturas de la interfaz.

Las reglas se han comprobado con el emulador (14 verificaciones de autorización y
esquema) y su ejecución forma parte del workflow Tests. Las pruebas de interfaz usan
Firebase simulado; no realizan escrituras en producción. Las reglas deben publicarse
en el proyecto real para habilitar la sincronización.

## Qué estaba mal (verificado en el código y en Chromium)

1. La contraseña por defecto era **`admin123`**, escrita en el propio `index.html`.
2. Se comparaba **en el navegador** (`checkPw`): cualquiera puede leerla en el código fuente o saltarse el formulario.
3. El estado completo `D`, **incluida la contraseña en claro**, se guardaba en Firestore (`portfolio/main`) con
   `JSON.stringify(d)`. Ese documento lo lee **cada visitante** (`getDoc`) y quedaba cacheado en su `localStorage`.
   Prueba: el payload de `setDoc` contenía `"password":"admin123"`.
4. `openAdmin` estaba expuesta en `window`: `window.openAdmin()` abría el panel sin contraseña.
5. `setLang()` (cambiar el idioma) llamaba a `save()`, que escribía el documento entero en Firestore: **un visitante
   anónimo podía provocar escrituras en el documento compartido**.
6. `index_.html` (copia antigua) sigue publicado con el mismo problema.
7. `.github/secret_scanning.yml` excluye `index.html` del escaneo de secretos de GitHub.

## Qué cambia en el código

- El admin se autentica con **Firebase Authentication (email + contraseña)**. La página ya no conoce ninguna contraseña.
- Se elimina `password` del estado, del `localStorage` y de lo que se publica en Firestore. Al cargar, se descarta si
  llega del documento remoto.
- Los visitantes **nunca escriben** en Firestore (`DB.set` solo escribe en remoto con sesión de admin).
- `openAdmin` ya no es global y comprueba la sesión; si la sesión se pierde mientras el admin está abierto, se cierra.
- Gate accesible (`role="dialog"`, etiquetas reales), mensaje de error genérico (no revela si el email existe) y bloqueo
  local de 30 s tras 5 fallos.
- La primera vez que entres como admin, si el documento remoto aún trae la contraseña antigua, se **reescribe limpio**
  automáticamente.
- Se quitó el campo «New admin password» de Ajustes y se añadió «Cerrar sesión de administrador».

> Este chequeo en el cliente es solo defensa en profundidad. **La protección real son las reglas de Firestore.**

## Lo que tienes que hacer tú (no puedo hacerlo desde aquí)

1. **Firebase Console → Authentication → Sign-in method**: activa *Email/Password*.
2. **Authentication → Users → Add user**: crea tu usuario administrador (contraseña nueva y larga). Si tu consola
   ofrece *User actions → Enable create (sign-up)*, desactívalo para que nadie pueda registrarse.
3. `firestore.rules` ya identifica al administrador por su UID de Authentication:
   `ylQ3m3XoCHTd0cwP7UQet7cSRpt1`. Copia el archivo completo a Firestore Database > Rules y pulsa Publish.
   Solo ese UID puede escribir en `portfolio/main`; la lectura sigue siendo publica.
4. Estas reglas comprueban el UID exacto y no requieren verificar el email. El panel exige el mismo UID.
   Publica tambien los cambios de index.html en GitHub Pages para actualizar el cliente.
5. **Cambia la contraseña** de cualquier otro servicio donde usaras la antigua.
6. Opcional: borra `index_.html` (`git rm index_.html`) y revisa si `secret_scanning.yml` debe seguir excluyendo `index.html`.
   La clave de la API web de Firebase **no es un secreto** (va en cualquier web con Firebase); lo que protege los datos
   son las reglas.

## Qué se probó y qué no

Probado (Chromium, Firebase **simulado**): ausencia de contraseña en el código, en `localStorage` y en los payloads;
`openAdmin` no global; credenciales incorrectas/vacías/email desconocido; bloqueo tras 5 fallos; login correcto; cierre de
sesión y pérdida de sesión; visitantes sin escrituras; limpieza del documento heredado; el panel de empleo del admin no se
monta sin sesión. Ver `tests/e2e/test_admin_security.py`.

**No probado:** las reglas reales de Firestore, tu proyecto Firebase, el proveedor de Auth ni la entrega de emails.
Hasta que publiques las reglas, el cliente impide escribir, pero **el servidor no**.
