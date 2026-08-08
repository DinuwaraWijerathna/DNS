from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_generate_keypair_and_sign_register_payload() -> None:
    domain = f"signed-{uuid4().hex[:10]}.bd"
    with TestClient(app) as client:
        keypair_res = client.post("/api/v1/crypto/keypair", json={})
        assert keypair_res.status_code == 200
        keypair = keypair_res.json()
        assert "private_key" in keypair
        assert "public_key" in keypair

        sign_res = client.post(
            "/api/v1/crypto/sign",
            json={
                "private_key": keypair["private_key"],
                "tx_type": "register",
                "domain": domain.upper(),
                "payload": {"ip": "203.0.113.77"},
            },
        )
        assert sign_res.status_code == 200
        signed = sign_res.json()
        assert signed["owner_public_key"] == keypair["public_key"]
        assert signed["normalized_domain"] == domain
        assert len(signed["signature"]) > 20

        register_res = client.post(
            "/api/v1/domains/register",
            json={
                "domain": signed["normalized_domain"],
                "ip": "203.0.113.77",
                "owner_public_key": signed["owner_public_key"],
                "signature": signed["signature"],
            },
        )
        assert register_res.status_code == 201


def test_sign_payload_rejects_invalid_private_key() -> None:
    with TestClient(app) as client:
        sign_res = client.post(
            "/api/v1/crypto/sign",
            json={
                "private_key": "abcd",
                "tx_type": "register",
                "domain": "bad.bd",
                "payload": {"ip": "203.0.113.2"},
            },
        )
        assert sign_res.status_code == 400
