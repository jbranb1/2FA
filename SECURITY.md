# Notas de seguridad

## Alcance

MFA Lab es código educativo para ejecución local. No debe exponerse a Internet sin rediseñar su configuración, almacenamiento de sesión y recuperación de cuentas.

## Decisiones implementadas

- Contraseñas almacenadas con Argon2.
- Secreto TOTP cifrado antes de guardarse en SQLite.
- Un secreto independiente por usuario.
- Desafíos JWT de cinco minutos separados del token de acceso.
- Claims type, purpose y auth_version validados en cada transición.
- Rechazo del mismo contador TOTP después de un uso exitoso.
- Tolerancia de reloj limitada a un periodo.
- Limitador local de intentos.
- CORS restringido por defecto a http://localhost:4200 y http://127.0.0.1:4200.
- Reinicio de TOTP condicionado por DEMO_MODE y una clave explícita.

## Simplificaciones deliberadas

- La clave JWT tiene un valor local predeterminado.
- El token se conserva en sessionStorage.
- El limitador de intentos vive en memoria y no se comparte entre procesos.
- No se implementan códigos de recuperación.
- No existe revocación centralizada salvo auth_version al reiniciar TOTP.
- El usuario demo y su contraseña están documentados.
- La clave de reinicio aparece en el frontend.

## Antes de producción

1. Desactivar DEMO_MODE y eliminar completamente el endpoint /api/dev/reset-totp.
2. Usar TLS y secretos gestionados por un servicio de claves.
3. Rotar claves JWT y separar la clave de cifrado TOTP.
4. Preferir cookies Secure, HttpOnly y SameSite con protección CSRF cuando corresponda.
5. Implementar rate limiting compartido y alertas de fuerza bruta.
6. Añadir códigos de recuperación de un solo uso y un proceso de soporte auditado.
7. Registrar eventos sin escribir contraseñas, secretos, QR, códigos ni tokens.
8. Aplicar políticas de sesión, revocación y rotación de refresh tokens.
9. Sincronizar relojes de servidores mediante una fuente confiable.
10. Someter el diseño a revisión de amenazas y pruebas de penetración.

## Incidente por exposición del QR

Si un QR o la clave Base32 se filtran, deben considerarse comprometidos. La respuesta correcta es revocar el secreto, invalidar sesiones, generar uno nuevo y revisar los registros de acceso.
