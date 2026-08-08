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


def test_resolver_cache_metrics_and_invalidation() -> None:
    domain = f"resolve-{uuid4().hex[:10]}.bd"
    owner_signing_key, owner_public_key = _new_keypair()

    with TestClient(app) as client:
        register_res = client.post(
            "/api/v1/domains/register",
            json={
                "domain": domain,
                "ip": "198.51.100.20",
                "owner_public_key": owner_public_key,
                "signature": _signature(
                    signing_key=owner_signing_key,
                    tx_type="register",
                    domain=domain,
                    payload={"ip": "198.51.100.20"},
                ),
            },
        )
        assert register_res.status_code == 201

        first_lookup = client.get(f"/api/v1/resolver/{domain}")
        assert first_lookup.status_code == 200
        assert first_lookup.json()["ip"] == "198.51.100.20"
        assert first_lookup.json()["source"] == "ledger"

        second_lookup = client.get(f"/api/v1/resolver/{domain}")
        assert second_lookup.status_code == 200
        assert second_lookup.json()["source"] == "cache"

        metrics = client.get("/api/v1/resolver/metrics/summary")
        assert metrics.status_code == 200
        metrics_body = metrics.json()
        assert metrics_body["total_queries"] >= 2
        assert metrics_body["cache_hits"] >= 1
        assert metrics_body["cache_misses"] >= 1

        update_res = client.put(
            f"/api/v1/domains/{domain}/ip",
            json={
                "ip": "198.51.100.21",
                "owner_public_key": owner_public_key,
                "signature": _signature(
                    signing_key=owner_signing_key,
                    tx_type="update",
                    domain=domain,
                    payload={"ip": "198.51.100.21"},
                ),
            },
        )
        assert update_res.status_code == 200

        after_update_lookup = client.get(f"/api/v1/resolver/{domain}")
        assert after_update_lookup.status_code == 200
        assert after_update_lookup.json()["ip"] == "198.51.100.21"
        assert after_update_lookup.json()["source"] == "ledger"

        logs = client.get("/api/v1/resolver/logs/recent?limit=10")
        assert logs.status_code == 200
        logs_body = logs.json()
        assert len(logs_body) >= 3
        latest = logs_body[-1]
        assert latest["domain"] == domain
        assert isinstance(latest["response_time_ms"], float)
