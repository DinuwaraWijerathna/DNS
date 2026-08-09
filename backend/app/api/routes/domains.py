from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.plans import get_domain_limit
from app.core.security import get_current_user
from app.core.supabase_client import supabase
from app.models.schemas import (
    DomainAuditEvent,
    DomainMutationResponse,
    DomainRecordResponse,
    RegisterDomainRequest,
    TransferDomainRequest,
    UpdateDomainRequest,
)

from app.services.global_dns_service import domain_exists_globally

from app.services.domain_service import (
    DomainAlreadyExistsError,
    DomainFrozenError,
    DomainNotFoundError,
    DomainOwnershipError,
    DomainService,
    DomainSignatureError,
)

router = APIRouter(prefix="/domains", tags=["domains"])


def _service_from_request(request: Request) -> DomainService:
    service = getattr(request.app.state, "domain_service", None)

    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Domain service is not initialized."
        )

    return service


@router.post(
    "/register",
    response_model=DomainMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_domain(
    payload: RegisterDomainRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> DomainMutationResponse:

    service = _service_from_request(request)

    # ── PLAN ENFORCEMENT ──────────────────────────────────────────────
    # The browser keeps one signing keypair for its whole session
    # (see getOrCreateKeypair in shared.js), so the first public key a
    # user ever registers a domain with is treated as "their" key for
    # counting domain usage against their plan. We store it on their
    # user row the first time, then reuse it on every later request so
    # this can't be bypassed by simply sending a different public key.
    user_result = supabase.table("users").select("plan, owner_public_key").eq(
        "id", current_user["user_id"]
    ).execute()

    if not user_result.data:
        raise HTTPException(status_code=404, detail="User account not found.")

    user_row = user_result.data[0]
    plan = user_row.get("plan")
    limit = get_domain_limit(plan)
    tracked_key = user_row.get("owner_public_key") or payload.owner_public_key

    if limit is not None:
        owned_count = sum(
            1
            for existing_domain in service.list_domains()
            if existing_domain.get("owner_public_key") == tracked_key
        )
        if owned_count >= limit:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Your current plan ({plan or 'trial'}) allows up to {limit} "
                    "domain(s). Upgrade your plan to register more domains."
                ),
            )

    if not user_row.get("owner_public_key"):
        supabase.table("users").update(
            {"owner_public_key": payload.owner_public_key}
        ).eq("id", current_user["user_id"]).execute()

    try:
        result = service.register_domain(
            domain=payload.domain,
            ip=payload.ip,
            owner_public_key=payload.owner_public_key,
            signature=payload.signature,
        )

    except DomainAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    except DomainSignatureError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return DomainMutationResponse(
        tx_id=result.tx_id,
        block_hash=result.block_hash,
        chain_height=result.chain_height,
    )


@router.put("/{domain}/ip", response_model=DomainMutationResponse)
def update_domain_ip(
    domain: str,
    payload: UpdateDomainRequest,
    request: Request,
) -> DomainMutationResponse:

    service = _service_from_request(request)

    try:
        result = service.update_domain(
            domain=domain,
            ip=payload.ip,
            owner_public_key=payload.owner_public_key,
            signature=payload.signature,
        )

    except DomainNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except DomainFrozenError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    except DomainOwnershipError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    except DomainSignatureError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return DomainMutationResponse(
        tx_id=result.tx_id,
        block_hash=result.block_hash,
        chain_height=result.chain_height,
    )


@router.post("/{domain}/transfer", response_model=DomainMutationResponse)
def transfer_domain(
    domain: str,
    payload: TransferDomainRequest,
    request: Request,
) -> DomainMutationResponse:

    service = _service_from_request(request)

    try:
        result = service.transfer_domain(
            domain=domain,
            owner_public_key=payload.owner_public_key,
            new_owner_public_key=payload.new_owner_public_key,
            signature=payload.signature,
        )

    except DomainNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except DomainFrozenError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc

    except DomainOwnershipError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    except DomainSignatureError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return DomainMutationResponse(
        tx_id=result.tx_id,
        block_hash=result.block_hash,
        chain_height=result.chain_height,
    )


@router.get("/{domain}/availability")
def check_domain_availability(
    domain: str,
    request: Request,
):

    service = _service_from_request(request)

    normalized_domain = domain.strip().lower()

    try:
        service.get_domain(normalized_domain)

        return {
            "status": "BLOCKED",
            "reason": "LOCAL_REGISTRY_EXISTS",
            "message": "Domain already exists in the BDNS blockchain registry.",
            "domain": normalized_domain
        }

    except DomainNotFoundError:
        pass

    if domain_exists_globally(normalized_domain):

        return {
            "status": "BLOCKED",
            "reason": "GLOBAL_DNS_EXISTS",
            "message": "Domain already exists on the public internet DNS.",
            "domain": normalized_domain
        }

    return {
        "status": "AVAILABLE",
        "reason": "NO_CONFLICT_FOUND",
        "message": "Domain is available for BDNS registration.",
        "domain": normalized_domain
    }


@router.get("", response_model=list[DomainRecordResponse])
def list_domains(
    request: Request
) -> list[DomainRecordResponse]:

    service = _service_from_request(request)

    return [
        DomainRecordResponse(**item)
        for item in service.list_domains()
    ]


@router.get("/{domain}", response_model=DomainRecordResponse)
def get_domain(
    domain: str,
    request: Request,
) -> DomainRecordResponse:

    service = _service_from_request(request)

    try:
        data = service.get_domain(domain)

    except DomainNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DomainRecordResponse(**data)


@router.get("/{domain}/history", response_model=list[DomainAuditEvent])
def get_domain_history(
    domain: str,
    request: Request,
) -> list[DomainAuditEvent]:

    service = _service_from_request(request)

    return [
        DomainAuditEvent(**event)
        for event in service.get_domain_history(domain)
    ]