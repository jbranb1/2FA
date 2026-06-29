from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    demo_mode: bool = _as_bool(os.getenv("DEMO_MODE"), True)
    demo_username: str = os.getenv("DEMO_USERNAME", "demo")
    demo_password: str = os.getenv("DEMO_PASSWORD", "Demo2FA!2026")
    demo_reset_key: str = os.getenv("DEMO_RESET_KEY", "local-demo-reset")
    jwt_secret: str = os.getenv(
        "JWT_SECRET", "local-demo-jwt-secret-change-me-32bytes-minimum"
    )
    database_path: Path = Path(
        os.getenv("DATABASE_PATH", str(BACKEND_DIR / "data" / "mfa_demo.db"))
    ).resolve()
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:4200")
    issuer: str = "MFA Lab"
    challenge_minutes: int = 5
    access_minutes: int = 30
    totp_interval: int = 30
    totp_digits: int = 6


settings = Settings()
