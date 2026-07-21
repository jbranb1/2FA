from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pyotp
from fastapi.testclient import TestClient

from app import security
from app.main import app


def test_cors_allows_both_local_frontend_hostnames():
    with TestClient(app) as client:
        for origin in ("http://localhost:4200", "http://127.0.0.1:4200"):
            response = client.options(
                "/api/health",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                },
            )

            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin


def test_complete_enrollment_login_replay_and_reset(monkeypatch):
    base_time = 2_000_000_000
    monkeypatch.setattr(security.time, "time", lambda: base_time)

    with TestClient(app) as client:
        reset = client.post(
            "/api/dev/reset-totp",
            json={"username": "demo"},
            headers={"X-Demo-Key": "local-demo-reset"},
        )
        assert reset.status_code == 200

        wrong = client.post(
            "/api/auth/login", json={"username": "demo", "password": "incorrecta"}
        )
        assert wrong.status_code == 401

        login = client.post(
            "/api/auth/login", json={"username": "demo", "password": "Demo2FA!2026"}
        )
        assert login.status_code == 200
        assert login.json()["next_step"] == "SETUP_REQUIRED"
        challenge = login.json()["challenge_token"]

        setup = client.post("/api/auth/totp/setup", json={"challenge_token": challenge})
        assert setup.status_code == 200
        assert setup.json()["qr_data_url"].startswith("data:image/svg+xml;base64,")
        uri = setup.json()["provisioning_uri"]
        secret = parse_qs(urlparse(uri).query)["secret"][0]
        first_code = pyotp.TOTP(secret).at(base_time)

        confirm = client.post(
            "/api/auth/totp/confirm",
            json={"challenge_token": challenge, "code": first_code},
        )
        assert confirm.status_code == 200
        access = confirm.json()["access_token"]

        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert me.status_code == 200
        assert me.json()["totp_enabled"] is True

        second_login = client.post(
            "/api/auth/login", json={"username": "demo", "password": "Demo2FA!2026"}
        )
        assert second_login.json()["next_step"] == "TOTP_REQUIRED"
        second_challenge = second_login.json()["challenge_token"]

        replay = client.post(
            "/api/auth/totp/verify",
            json={"challenge_token": second_challenge, "code": first_code},
        )
        assert replay.status_code == 409

        monkeypatch.setattr(security.time, "time", lambda: base_time + 30)
        next_code = pyotp.TOTP(secret).at(base_time + 30)
        verify = client.post(
            "/api/auth/totp/verify",
            json={"challenge_token": second_challenge, "code": next_code},
        )
        assert verify.status_code == 200

        reset_again = client.post(
            "/api/dev/reset-totp",
            json={"username": "demo"},
            headers={"X-Demo-Key": "local-demo-reset"},
        )
        assert reset_again.status_code == 200
        invalidated = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {access}"}
        )
        assert invalidated.status_code == 401

        enrollment_again = client.post(
            "/api/auth/login", json={"username": "demo", "password": "Demo2FA!2026"}
        )
        assert enrollment_again.json()["next_step"] == "SETUP_REQUIRED"
