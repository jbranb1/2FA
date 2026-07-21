from __future__ import annotations

import base64
from contextlib import asynccontextmanager
from io import BytesIO
from typing import Annotated, Literal

import jwt
import qrcode
import qrcode.image.svg
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .config import settings
from .database import UserRepository
from .security import AttemptLimiter, TokenService, TotpService, hash_password, verify_password


repository = UserRepository(settings.database_path)
tokens = TokenService(settings)
totp = TotpService(settings)
limiter = AttemptLimiter()
bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class ChallengeRequest(BaseModel):
    challenge_token: str


class CodeRequest(ChallengeRequest):
    code: str = Field(pattern=r"^\d{6}$")


class ResetRequest(BaseModel):
    username: str = Field(default="demo", min_length=1, max_length=100)


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def user_for_challenge(token: str, purpose: Literal["enroll", "verify"]):
    try:
        claims = tokens.decode(token, "challenge")
    except jwt.PyJWTError as exc:
        raise unauthorized("El desafío expiró o no es válido") from exc
    if claims.get("purpose") != purpose:
        raise unauthorized("El desafío no corresponde a este paso")
    user = repository.get_by_username(str(claims.get("sub", "")))
    if not user or user["auth_version"] != claims.get("ver"):
        raise unauthorized("El desafío fue invalidado")
    return user


def require_access(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
):
    if credentials is None:
        raise unauthorized("Se requiere una sesión autenticada")
    try:
        claims = tokens.decode(credentials.credentials, "access")
    except jwt.PyJWTError as exc:
        raise unauthorized("La sesión expiró o no es válida") from exc
    user = repository.get_by_username(str(claims.get("sub", "")))
    if not user or user["auth_version"] != claims.get("ver"):
        raise unauthorized("La sesión fue invalidada")
    return user


def make_qr_data_url(uri: str) -> str:
    image = qrcode.make(
        uri,
        image_factory=qrcode.image.svg.SvgPathImage,
        box_size=8,
        border=3,
    )
    buffer = BytesIO()
    image.save(buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


@asynccontextmanager
async def lifespan(_: FastAPI):
    repository.initialize()
    repository.create_demo_user(settings.demo_username, hash_password(settings.demo_password))
    yield


app = FastAPI(
    title="MFA Lab API",
    description="Backend educativo para comprender MFA con TOTP.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Demo-Key"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "demo_mode": settings.demo_mode}


@app.post("/api/auth/login")
def login(payload: LoginRequest, request: Request):
    client = request.client.host if request.client else "unknown"
    limit_key = f"login:{client}:{payload.username}"
    if not limiter.allowed(limit_key):
        raise HTTPException(status_code=429, detail="Demasiados intentos; espera un minuto")

    user = repository.get_by_username(payload.username)
    if not user or not verify_password(user["password_hash"], payload.password):
        raise unauthorized("Usuario o contraseña incorrectos")

    limiter.clear(limit_key)
    if user["totp_enabled"]:
        return {
            "next_step": "TOTP_REQUIRED",
            "challenge_token": tokens.challenge(payload.username, "verify", user["auth_version"]),
            "message": "Credenciales correctas. Ingresa el código de tu autenticador.",
        }

    if not user["totp_secret_encrypted"]:
        repository.set_pending_secret(payload.username, totp.encrypt(totp.generate_secret()))
    return {
        "next_step": "SETUP_REQUIRED",
        "challenge_token": tokens.challenge(payload.username, "enroll", user["auth_version"]),
        "message": "Debes registrar un autenticador antes de continuar.",
    }


@app.post("/api/auth/totp/setup")
def totp_setup(payload: ChallengeRequest):
    user = user_for_challenge(payload.challenge_token, "enroll")
    if user["totp_enabled"] or not user["totp_secret_encrypted"]:
        raise HTTPException(status_code=409, detail="El enrolamiento ya no está disponible")
    secret = totp.decrypt(user["totp_secret_encrypted"])
    uri = totp.provisioning_uri(secret, user["username"])
    return {
        "qr_data_url": make_qr_data_url(uri),
        "manual_key": secret,
        "provisioning_uri": uri,
        "issuer": settings.issuer,
        "account": user["username"],
        "period_seconds": settings.totp_interval,
        "digits": settings.totp_digits,
    }


@app.post("/api/auth/totp/confirm")
def totp_confirm(payload: CodeRequest):
    user = user_for_challenge(payload.challenge_token, "enroll")
    if not user["totp_secret_encrypted"]:
        raise HTTPException(status_code=409, detail="No existe un secreto pendiente")
    counter = totp.match_counter(totp.decrypt(user["totp_secret_encrypted"]), payload.code)
    if counter is None:
        raise unauthorized("Código incorrecto o fuera de la ventana de tiempo")
    repository.enable_totp(user["username"], counter)
    return {
        "access_token": tokens.access(user["username"], user["auth_version"]),
        "token_type": "bearer",
        "expires_in": settings.access_minutes * 60,
        "message": "TOTP quedó configurado correctamente.",
    }


@app.post("/api/auth/totp/verify")
def totp_verify(payload: CodeRequest, request: Request):
    user = user_for_challenge(payload.challenge_token, "verify")
    client = request.client.host if request.client else "unknown"
    limit_key = f"totp:{client}:{user['username']}"
    if not limiter.allowed(limit_key):
        raise HTTPException(status_code=429, detail="Demasiados códigos; espera un minuto")
    if not user["totp_enabled"] or not user["totp_secret_encrypted"]:
        raise HTTPException(status_code=409, detail="TOTP no está configurado")

    counter = totp.match_counter(totp.decrypt(user["totp_secret_encrypted"]), payload.code)
    if counter is None:
        raise unauthorized("Código incorrecto o fuera de la ventana de tiempo")
    if user["last_totp_counter"] is not None and counter <= user["last_totp_counter"]:
        raise HTTPException(status_code=409, detail="Este código ya fue utilizado; espera el siguiente")

    repository.update_last_counter(user["username"], counter)
    limiter.clear(limit_key)
    return {
        "access_token": tokens.access(user["username"], user["auth_version"]),
        "token_type": "bearer",
        "expires_in": settings.access_minutes * 60,
        "message": "Segundo factor validado.",
    }


@app.get("/api/auth/me")
def me(user=Depends(require_access)):
    return {
        "username": user["username"],
        "totp_enabled": bool(user["totp_enabled"]),
        "totp_configured_at": user["totp_configured_at"],
    }


@app.post("/api/auth/logout")
def logout(_: object = Depends(require_access)):
    return {"message": "Sesión cerrada en el cliente."}


@app.post("/api/dev/reset-totp")
def reset_totp(
    payload: ResetRequest,
    x_demo_key: Annotated[str | None, Header()] = None,
):
    if not settings.demo_mode:
        raise HTTPException(status_code=404, detail="No disponible")
    if not hmac_compare(x_demo_key, settings.demo_reset_key):
        raise HTTPException(status_code=403, detail="Clave de demostración incorrecta")
    if not repository.reset_totp(payload.username):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {
        "message": "TOTP eliminado. El siguiente login iniciará un enrolamiento nuevo.",
        "username": payload.username,
    }


def hmac_compare(received: str | None, expected: str) -> bool:
    import hmac

    return received is not None and hmac.compare_digest(received, expected)
