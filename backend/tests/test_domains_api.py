from uuid import uuid4

from ecdsa import NIST256p, SigningKey
from fastapi.testclient import TestClient

from app.crypto.signature_service import SignatureService
from app.main import app


def _new_keypair() -> tuple[SigningKey, str]:
    signing_key = SigningKey.generate(curve=NIST256p)
    return signing_key, signing_key.verifying_key.to_string().hex()


def _signature(
    *,
    signing_key: SigningKey,
    tx_type: str,
    domain: str,
    payload: dict[str, str],
) -> str:
    message = SignatureService.build_signing_message(
        tx_type=tx_type,
        domain=domain,
        payload=payload,
    )
    return signing_key.sign(message.encode("utf-8")).hex()


def test_register_query_update_transfer_and_audit_flow() -> None:
    domain = f"phase2-{uuid4().hex[:10]}.bd"
    owner_signing_key, owner_public_key = _new_keypair()
    new_owner_signing_key, new_owner_public_key = _new_keypair()

    with TestClient(app) as client:
        register_payload = {
            "domain": domain,
            "ip": "203.0.113.55",
            "owner_public_key": owner_public_key,
            "signature": _signature(
                signing_key=owner_signing_key,
                tx_type="register",
                domain=domain,
                payload={"ip": "203.0.113.55"},
            ),
        }
        register_res = client.post("/api/v1/domains/register", json=register_payload)
        assert register_res.status_code == 201

        domain_res = client.get(f"/api/v1/domains/{domain}")
        assert domain_res.status_code == 200
        assert domain_res.json()["ip"] == "203.0.113.55"
        assert domain_res.json()["owner_public_key"] == owner_public_key

        bad_update = client.put(
            f"/api/v1/domains/{domain}/ip",
            json={
                "ip": "203.0.113.99",
                "owner_public_key": owner_public_key,
                "signature": "deadbeef",
            },
        )
        assert bad_update.status_code == 401

        update_res = client.put(
            f"/api/v1/domains/{domain}/ip",
            json={
                "ip": "203.0.113.99",
                "owner_public_key": owner_public_key,
                "signature": _signature(
                    signing_key=owner_signing_key,
                    tx_type="update",
                    domain=domain,
                    payload={"ip": "203.0.113.99"},
                ),
            },
        )
        assert update_res.status_code == 200

        transfer_res = client.post(
            f"/api/v1/domains/{domain}/transfer",
            json={
                "new_owner_public_key": new_owner_public_key,
                "owner_public_key": owner_public_key,
                "signature": _signature(
                    signing_key=owner_signing_key,
                    tx_type="transfer",
                    domain=domain,
                    payload={"new_owner_public_key": new_owner_public_key},
                ),
            },
        )
        assert transfer_res.status_code == 200

        old_owner_update_res = client.put(
            f"/api/v1/domains/{domain}/ip",
            json={
                "ip": "203.0.113.111",
                "owner_public_key": owner_public_key,
                "signature": _signature(
                    signing_key=owner_signing_key,
                    tx_type="update",
                    domain=domain,
                    payload={"ip": "203.0.113.111"},
                ),
            },
        )
        assert old_owner_update_res.status_code == 403

        new_owner_update_res = client.put(
            f"/api/v1/domains/{domain}/ip",
            json={
                "ip": "203.0.113.120",
                "owner_public_key": new_owner_public_key,
                "signature": _signature(
                    signing_key=new_owner_signing_key,
                    tx_type="update",
                    domain=domain,
                    payload={"ip": "203.0.113.120"},
                ),
            },
        )
        assert new_owner_update_res.status_code == 200

        updated_domain_res = client.get(f"/api/v1/domains/{domain}")
        assert updated_domain_res.status_code == 200
        assert updated_domain_res.json()["owner_public_key"] == new_owner_public_key
        assert updated_domain_res.json()["ip"] == "203.0.113.120"

        history_res = client.get(f"/api/v1/domains/{domain}/history")
        assert history_res.status_code == 200
        history = history_res.json()
        assert len(history) == 4
        assert [event["tx_type"] for event in history] == [
            "register",
            "update",
            "transfer",
            "update",
        ]
