# VFX Job Tracker — auditoría y parche v1 (20 octubre 2026)

## Resultado de la auditoría
- En el snapshot del 8/10/2026: 23 compañías, 4 errores de escaneo, 68 registros activos; 52 con workplace `unknown`. Los datos NO prueban que estén abiertas hoy.
- El sistema no conoce con certeza la modalidad contractual ni la contratación desde España. **No equiparar «remoto» con «remoto desde España».**
- El administrador compara `D.password` en JavaScript. La contraseña por defecto aparece en el HTML y datos de administración pueden quedar accesibles desde el navegador. **No es autenticación real.** No guardar credenciales, datos de candidaturas privadas ni secretos en el frontend público. Cambiar contraseña no soluciona la exposición; requiere backend autenticado (por ejemplo Firebase Auth + Security Rules correctas, o un backend privado). Auditar reglas y datos publicados antes de desplegar.

## Cambios implementados
1. No perder registros tras un fallo de escaneo: `unverified`, separado de `active` y `closed`.
2. No cerrar registros de agregadores solo porque no reaparecen en una búsqueda limitada.
3. No reemplazar enlaces específicos a vacantes por la home de empleo: `discoveredCareersUrl` guarda la pista de empresa separadamente.
4. No descartar del índice las vacantes UK/US-only por título: conservarlas para auditar; se indica la restricción en el nuevo campo de compatibilidad si hay evidencia.
5. Primer campo **heurístico** `spainEligibility` (promising / review / unknown / restricted) y motivo. **Promising NO significa contrato confirmado.**
6. Filtro de compatibilidad de España y posibilidad de incluir registros `unverified` en el navegador.
7. Escapado de campos de vacantes en el listado para reducir riesgos de inyección HTML. URL limitada a HTTP/HTTPS.
8. Corregido `uses_reliable_api` de Teamtailor, que en esta versión usa scraping HTML.
9. Priorización de país en `detect_remote_scope` y de modalidad híbrida cuando aparece «remote hybrid».
10. Pruebas automatizadas nuevas y actualización de pruebas sobre el enlace al ATS.

## Limitaciones y recomendaciones IMPORTANTES
- El texto de las descripciones es poco uniforme y muchos adaptadores NO aportan `description`. Por ello predominará `unknown` hasta enriquecer correctamente los datos.
- `detect_remote_scope` basado en palabras puede confundir «global company» con «global remote». NO usarlo como condición jurídica.
- «Spain possible» solo identifica una pista: falta confirmar contrato de empleado, prueba, duración, salario, exclusividad y entidad empleadora.
- Las vacantes antiguas en `jobs.json` no adquieren retroactivamente `spainEligibility`; se clasificarán «Sin confirmar» en la interfaz hasta el próximo escaneo exitoso.
- Las ofertas de Adzuna se conservan enlazadas al anuncio original; `discoveredCareersUrl` no acredita la vacante.
- La ejecución GitHub Actions no se ha podido ejecutar ni comprobar frente a los sitios externos de contratación desde este entorno.
- Tampoco se ha probado el login real ni las reglas del backend Firebase. **No publicar datos personales nuevos en el frontend público.**

## Próxima fase — empleo desde España
1. Ampliar y verificar fuentes ATS con empresas que contraten asalariados desde España; controlar errores, rate limits, fechas y paginación.
2. Extraer descripción completa + condiciones y citar evidencia por frase: residencia, contrato, EOR, jornada, temporalidad, hybrid, relocation y salario.
3. Filtro con etiquetas `verified`, `likely`, `unknown`, `not eligible`. **Nunca aplicar descartes irreversibles con regex.**
4. Separar fichas de empresas de vacantes verificadas y mejorar identificación por URL/ATS ID.
5. Registrar candidatura y respuesta en un backend PRIVADO, no en el JSON público.

## App Android
Reutilizar el mismo scanner Python y las salidas normalizadas como backend/fuente de datos. Crear cliente Flutter Android (o PWA antes) que consuma una API/JSON de solo lectura, con favoritos, notificaciones y candidaturas almacenadas PRIVADAMENTE (auth + reglas). No portar a Dart los 11 adaptadores: eso duplicaría mantenimiento y requeriría peticiones a ATS desde el teléfono. Separar datos públicos de vacantes y datos privados del usuario.

## Verificación
`python -m pytest -q` y validación sintáctica del JavaScript embebido con `node --check`.
