from __future__ import annotations

from ecdsa import NIST256p, SigningKey
from ecdsa.errors import MalformedPointError
from fastapi import APIRouter, HTTPException

from app.crypto.signature_service import SignatureService
from app.models.schemas import (
    GenerateKeypairResponse,
    SignPayloadRequest,
    SignPayloadResponse,
)

router = APIRouter(prefix="/crypto", tags=["crypto"])


@router.post("/keypair", response_model=GenerateKeypairResponse)
def generate_keypair() -> GenerateKeypairResponse:
    signing_key = SigningKey.generate(curve=NIST256p)
    return GenerateKeypairResponse(
        private_key=signing_key.to_string().hex(),
        public_key=signing_key.verifying_key.to_string().hex(),
    )


@router.post("/sign", response_model=SignPayloadResponse)
def sign_payload(payload: SignPayloadRequest) -> SignPayloadResponse:
    try:
        signing_key = SigningKey.from_string(bytes.fromhex(payload.private_key), curve=NIST256p)
    except (ValueError, MalformedPointError) as exc:
        raise HTTPException(status_code=400, detail="Invalid private key format.") from exc

    normalized_domain = payload.domain.strip().lower()
    message = SignatureService.build_signing_message(
        tx_type=payload.tx_type,
        domain=normalized_domain,
        payload=payload.payload,
    )
    signature = signing_key.sign(message.encode("utf-8")).hex()
    return SignPayloadResponse(
        owner_public_key=signing_key.verifying_key.to_string().hex(),
        signature=signature,
        normalized_domain=normalized_domain,
    )
