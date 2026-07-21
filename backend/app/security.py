from __future__ import annotations

import base64
import hashlib
import hmac
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from .config import Settings


password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, candidate: str) -> bool:
    try:
        return password_hasher.verify(password_hash, candidate)
    except VerifyMismatchError:
        return False


class TokenService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _encode(self, claims: dict[str, Any], minutes: int) -> str:
        now = datetime.now(UTC)
        payload = {
            **claims,
            "iat": now,
            "exp": now + timedelta(minutes=minutes),
        }
        return jwt.encode(payload, self.settings.jwt_secret, algorithm="HS256")

    def challenge(self, username: str, purpose: Literal["enroll", "verify"], version: int) -> str:
        return self._encode(
            {"sub": username, "type": "challenge", "purpose": purpose, "ver": version},
            self.settings.challenge_minutes,
        )

    def access(self, username: str, version: int) -> str:
        return self._encode(
            {"sub": username, "type": "access", "ver": version},
            self.settings.access_minutes,
        )

    def decode(self, token: str, expected_type: str) -> dict[str, Any]:
        payload = jwt.decode(token, self.settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != expected_type:
            raise jwt.InvalidTokenError("Tipo de token incorrecto")
        return payload


class TotpService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        key = hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()
        self.fernet = Fernet(base64.urlsafe_b64encode(key))

    def generate_secret(self) -> str:
        return pyotp.random_base32()

    def encrypt(self, secret: str) -> str:
        return self.fernet.encrypt(secret.encode("utf-8")).decode("ascii")

    def decrypt(self, encrypted_secret: str) -> str:
        try:
            return self.fernet.decrypt(encrypted_secret.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("No se pudo descifrar el secreto TOTP") from exc

    def provisioning_uri(self, secret: str, username: str) -> str:
        return pyotp.TOTP(
            secret,
            digits=self.settings.totp_digits,
            interval=self.settings.totp_interval,
        ).provisioning_uri(name=username, issuer_name=self.settings.issuer)

    def match_counter(self, secret: str, code: str) -> int | None:
        current_counter = int(time.time()) // self.settings.totp_interval
        generator = pyotp.TOTP(
            secret,
            digits=self.settings.totp_digits,
            interval=self.settings.totp_interval,
        )
        for offset in (-1, 0, 1):
            candidate_counter = current_counter + offset
            expected = generator.at(candidate_counter * self.settings.totp_interval)
            if hmac.compare_digest(expected, code):
                return candidate_counter
        return None


class AttemptLimiter:
    """Limitador local y educativo; producción requiere almacenamiento compartido."""

    def __init__(self, limit: int = 6, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.attempts: dict[str, deque[float]] = defaultdict(deque)

    def allowed(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self.attempts[key]
        while bucket and bucket[0] <= now - self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True

    def clear(self, key: str) -> None:
        self.attempts.pop(key, None)

