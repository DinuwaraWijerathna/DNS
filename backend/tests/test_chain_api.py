from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_submit_and_commit_transaction_flow() -> None:
    domain = f"chain-{uuid4().hex[:8]}.bd"
    with TestClient(app) as client:
        submit_res = client.post(
            "/api/v1/chain/transactions",
            json={
                "tx_type": "register",
                "domain": domain,
                "payload": {"ip": "203.0.113.10"},
                "owner_public_key": "owner-pub-key",
                "signature": "signed-payload",
            },
        )
        assert submit_res.status_code == 200
        assert "tx_id" in submit_res.json()

        commit_res = client.post("/api/v1/chain/commit", json={})
        assert commit_res.status_code == 200
        commit_body = commit_res.json()
        assert commit_body["chain_height"] >= 2
        assert any(tx["domain"] == domain for tx in commit_body["block"]["transactions"])


def test_commit_rejects_unauthorized_validator() -> None:
    with TestClient(app) as client:
        submit_res = client.post(
            "/api/v1/chain/transactions",
            json={
                "tx_type": "register",
                "domain": "invalid-validator.bd",
                "payload": {"ip": "198.51.100.8"},
                "owner_public_key": "owner-pub-key",
                "signature": "signed-payload",
            },
        )
        assert submit_res.status_code == 200

        commit_res = client.post("/api/v1/chain/commit", json={"validator": "not-authorized"})
        assert commit_res.status_code == 400
        assert commit_res.json()["detail"] == "Validator is not authorized."
