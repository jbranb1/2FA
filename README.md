# MFA Lab: Angular + FastAPI + TOTP

Proyecto educativo para observar el ciclo completo de autenticación de dos factores mediante códigos TOTP compatibles con Google Authenticator.

## Credenciales

- Usuario: **demo**
- Contraseña: **Demo2FA!2026**

Estas credenciales son públicas y existen únicamente para el laboratorio.

## Ejecución

Backend, desde backend:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python run.py

Frontend, desde frontend:

    npm install
    npm start

Abre http://localhost:4200. La documentación interactiva de la API está en http://localhost:8000/docs.

## Primer ingreso

1. Angular envía usuario y contraseña a POST /api/auth/login.
2. FastAPI verifica el hash Argon2 de la contraseña.
3. Como TOTP no está configurado, el servidor crea un secreto aleatorio y devuelve un desafío temporal de enrolamiento.
4. El frontend solicita POST /api/auth/totp/setup.
5. El backend construye una URI otpauth y la convierte en QR.
6. Google Authenticator guarda el secreto después de escanear el QR.
7. El usuario introduce el primer código.
8. POST /api/auth/totp/confirm verifica el código, activa TOTP y emite el token de acceso.

El QR no es un segundo factor por sí mismo. Es un mecanismo de aprovisionamiento que entrega el secreto compartido.

## Ingresos posteriores

1. El usuario vuelve a introducir usuario y contraseña.
2. El backend detecta que totp_enabled es verdadero.
3. Devuelve un desafío temporal con propósito verify, no un token de acceso.
4. Angular muestra únicamente el campo TOTP.
5. POST /api/auth/totp/verify valida el código.
6. Solo después se emite el token que permite entrar a /home.

## Cómo funciona TOTP

TOTP está definido por RFC 6238 y reutiliza HOTP. Ambos extremos tienen:

- el mismo secreto K;
- el tiempo Unix actual;
- el mismo intervalo X, aquí 30 segundos;
- el mismo algoritmo HMAC, aquí SHA-1 por compatibilidad;
- seis dígitos.

El contador temporal es:

    T = floor(UnixTime / 30)

La aplicación y el backend calculan independientemente:

    TOTP = Truncate(HMAC-SHA1(K, T)) mod 1,000,000

No existe una llamada desde Google Authenticator al backend. Si el reloj y el secreto coinciden, ambos obtienen el mismo valor.

## Qué contiene el QR

El QR representa una URI similar a:

    otpauth://totp/MFA%20Lab:demo?secret=BASE32&issuer=MFA%20Lab&period=30&digits=6

El parámetro secret es equivalente a una contraseña criptográfica. Quien copie el QR puede generar códigos válidos. Por eso el backend no vuelve a mostrarlo después de confirmar el enrolamiento.

## Estados del backend

| Estado | Respuesta después de la contraseña | Acción siguiente |
| --- | --- | --- |
| Sin secreto | SETUP_REQUIRED | Crear y mostrar QR |
| Secreto pendiente | SETUP_REQUIRED | Confirmar primer código |
| TOTP activo | TOTP_REQUIRED | Verificar código registrado |
| Dos factores válidos | Token de acceso | Permitir área protegida |

Los JWT de desafío incluyen un propósito específico: enroll o verify. No sirven para consultar rutas protegidas. Su duración es cinco minutos. El token final dura treinta minutos.

## Ventana temporal y reutilización

El servidor acepta el intervalo actual y un intervalo adyacente a cada lado para tolerar pequeños desfases de reloj. Una ventana mayor facilitaría ataques.

La tabla users conserva last_totp_counter. Si un código ya produjo una autenticación, el mismo contador se rechaza aunque el código todavía aparezca en el teléfono.

## Reinicio de la demostración

En la pantalla de login y en /home existe un botón para borrar TOTP. Este llama:

    POST /api/dev/reset-totp
    X-Demo-Key: local-demo-reset

El reinicio elimina el secreto, la fecha, el último contador y aumenta auth_version. Con ello también invalida desafíos y sesiones anteriores.

El endpoint solo existe cuando DEMO_MODE=true. Nunca debe publicarse de esta forma.

## Estructura

    frontend/              Angular 22
      src/app/core/        Contratos, sesión y guard
      src/app/pages/       Login, setup, verify y home
    backend/               FastAPI
      app/config.py        Configuración
      app/database.py      SQLite y estado del usuario
      app/security.py      Hash, JWT, cifrado y TOTP
      app/main.py          Endpoints HTTP
      tests/               Flujo completo automatizado

## Pruebas

Backend:

    cd backend
    .\.venv\Scripts\python -m pytest -q

Frontend:

    cd frontend
    npm test
    npm run build

La prueba del backend congela el tiempo y demuestra enrolamiento, autenticación posterior, rechazo de reutilización, siguiente código válido, reinicio e invalidación de sesión.

## Diferencias frente a producción

Este proyecto sí usa hash Argon2, cifra el secreto TOTP en SQLite, limita intentos localmente, separa desafíos de sesiones y evita reutilización.

Una implementación real todavía necesita HTTPS obligatorio, claves gestionadas fuera del repositorio, cookies HttpOnly o una estrategia endurecida de tokens, rate limiting compartido, auditoría, códigos de recuperación, revocación centralizada, protección CSRF cuando aplique y un proceso verificado para recuperar cuentas.

Consulta también SECURITY.md.
