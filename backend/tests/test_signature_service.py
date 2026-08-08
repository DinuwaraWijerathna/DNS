from ecdsa import NIST256p, SigningKey

from app.crypto.signature_service import SignatureService


def test_signature_service_verifies_valid_signature() -> None:
    signing_key = SigningKey.generate(curve=NIST256p)
    verifying_key = signing_key.verifying_key
    service = SignatureService()

    tx_type = "register"
    domain = "valid-sig.bd"
    payload = {"ip": "203.0.113.1"}
    message = service.build_signing_message(tx_type=tx_type, domain=domain, payload=payload)
    signature = signing_key.sign(message.encode("utf-8")).hex()

    assert service.verify_signature(
        tx_type=tx_type,
        domain=domain,
        payload=payload,
        owner_public_key=verifying_key.to_string().hex(),
        signature=signature,
    )


def test_signature_service_rejects_invalid_signature() -> None:
    signer_a = SigningKey.generate(curve=NIST256p)
    signer_b = SigningKey.generate(curve=NIST256p)
    service = SignatureService()

    message = service.build_signing_message(
        tx_type="register",
        domain="invalid-sig.bd",
        payload={"ip": "203.0.113.5"},
    )
    bad_signature = signer_b.sign(message.encode("utf-8")).hex()

    assert not service.verify_signature(
        tx_type="register",
        domain="invalid-sig.bd",
        payload={"ip": "203.0.113.5"},
        owner_public_key=signer_a.verifying_key.to_string().hex(),
        signature=bad_signature,
    )
