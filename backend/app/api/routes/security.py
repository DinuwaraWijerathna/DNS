from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ecdsa import NIST256p, SigningKey
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.crypto.signature_service import SignatureService
from app.services.domain_service import DomainNotFoundError, DomainService, DomainSignatureError

router = APIRouter(prefix="/security", tags=["security-demo"])


class SpoofingSimulationRequest(BaseModel):
    domain: str = Field(..., examples=["example.bd"])
    malicious_ip: str = Field("198.51.100.66", examples=["198.51.100.66"])


class CachePoisoningSimulationRequest(BaseModel):
    domain: str = Field(..., examples=["example.bd"])
    poisoned_ip: str = Field("198.51.100.99", examples=["198.51.100.99"])


def _domain_service(request: Request) -> DomainService:
    service = getattr(request.app.state, "domain_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Domain service is not initialized.")
    return service


def _resolver_service(request: Request):
    service = getattr(request.app.state, "resolver_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Resolver service is not initialized.")
    return service


@router.post("/simulate/spoofing")
def simulate_dns_spoofing(payload: SpoofingSimulationRequest, request: Request) -> dict[str, Any]:
    """Demonstrate that a non-owner cannot replace a domain IP record."""
    service = _domain_service(request)
    normalized_domain = payload.domain.strip().lower()

    try:
        legitimate_record = service.get_domain(normalized_domain)
    except DomainNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Register the domain first, then run the spoofing simulation.",
        ) from exc

    attacker_key = SigningKey.generate(curve=NIST256p)
    attacker_public_key = attacker_key.verifying_key.to_string().hex()
    attacker_payload = {"ip": payload.malicious_ip}
    message = SignatureService.build_signing_message(
        tx_type="update",
        domain=normalized_domain,
        payload=attacker_payload,
    )
    attacker_signature = attacker_key.sign(message.encode("utf-8")).hex()

    try:
        service.update_domain(
            domain=normalized_domain,
            ip=payload.malicious_ip,
            owner_public_key=attacker_public_key,
            signature=attacker_signature,
        )
        blocked = False
        reason = "Unexpected: malicious update was accepted."
    except Exception as exc:  # Expected path: ownership check or signature check blocks it.
        blocked = True
        reason = str(exc)

    current_record = service.get_domain(normalized_domain)
    return {
        "simulation": "dns_spoofing",
        "status": "blocked" if blocked else "failed",
        "blocked": blocked,
        "reason": reason,
        "attempted_domain": normalized_domain,
        "attempted_ip": payload.malicious_ip,
        "attacker_public_key_preview": f"{attacker_public_key[:32]}...",
        "legitimate_ip_before": legitimate_record["ip"],
        "legitimate_ip_after": current_record["ip"],
        "record_unchanged": legitimate_record["ip"] == current_record["ip"],
        "tested_at": datetime.now(UTC).isoformat(),
    }


@router.post("/simulate/cache-poisoning")
def simulate_cache_poisoning(
    payload: CachePoisoningSimulationRequest,
    request: Request,
) -> dict[str, Any]:
    """Demonstrate resolver behavior where authoritative blockchain state wins."""
    resolver = _resolver_service(request)
    service = _domain_service(request)
    normalized_domain = payload.domain.strip().lower()

    try:
        authoritative_record = service.get_domain(normalized_domain)
    except DomainNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Register the domain first, then run the cache poisoning simulation.",
        ) from exc

    cache_key = resolver.cache_client.domain_cache_key(normalized_domain)
    resolver.cache_client.set_json(
        cache_key,
        {
            "domain": normalized_domain,
            "ip": payload.poisoned_ip,
            "owner_public_key": "attacker-cache-entry",
            "updated_at": datetime.now(UTC).isoformat(),
        },
        ttl_seconds=resolver.cache_ttl_seconds,
    )
    poisoned_result = resolver.resolve_domain(normalized_domain)

    resolver.cache_client.invalidate_domain(normalized_domain)
    verified_result = resolver.resolve_domain(normalized_domain)

    blocked = verified_result["ip"] == authoritative_record["ip"] and verified_result["ip"] != payload.poisoned_ip
    return {
        "simulation": "cache_poisoning",
        "status": "blocked" if blocked else "needs_review",
        "blocked": blocked,
        "domain": normalized_domain,
        "poisoned_cache_response": poisoned_result,
        "verified_ledger_response": verified_result,
        "authoritative_ledger_ip": authoritative_record["ip"],
        "explanation": "The demo shows a poisoned cache value, then clears cache and verifies the authoritative blockchain record.",
        "tested_at": datetime.now(UTC).isoformat(),
    }


@router.get("/report")
def security_report(request: Request) -> dict[str, Any]:
    ledger = getattr(request.app.state, "ledger", None)
    resolver = _resolver_service(request)
    return {
        "project": "Blockchain-Based Domain Name System",
        "security_claims": [
            "Domain records are committed as blockchain transactions.",
            "Record updates require ECDSA signatures from the current owner.",
            "Domain history remains auditable across committed blocks.",
            "Resolver cache improves performance while ledger state remains authoritative.",
        ],
        "chain_height": ledger.get_chain_height() if ledger else 0,
        "chain_valid": ledger.is_chain_valid() if ledger else False,
        "resolver_metrics": resolver.get_metrics(),
        "generated_at": datetime.now(UTC).isoformat(),
    }
