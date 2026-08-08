from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.security import require_admin
from app.core.supabase_client import supabase
from app.models.schemas import (
    AdminFreezeRequest,
    AdminStatsResponse,
    AdminUserResponse,
    AdminUserStatusRequest,
    DomainMutationResponse,
    GlobalAuditEvent,
)
from app.services.domain_service import (
    DomainAlreadyActiveError,
    DomainAlreadyFrozenError,
    DomainNotFoundError,
    DomainService,
)

router = APIRouter(prefix="/admin", tags=["admin"])

ALLOWED_USER_STATUSES = {"active", "suspended"}


def _service_from_request(request: Request) -> DomainService:
    service = getattr(request.app.state, "domain_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Domain service is not initialized.")
    return service


# ─── USER MANAGEMENT ───────────────────────────────────────────

@router.get("/users", response_model=list[AdminUserResponse])
def list_users(request: Request, admin: dict = Depends(require_admin)) -> list[AdminUserResponse]:
    result = supabase.table("users").select("*").execute()
    users: list[dict[str, Any]] = result.data or []

    users.sort(key=lambda u: str(u.get("created_at") or ""), reverse=True)

    return [
        AdminUserResponse(
            user_id=str(u.get("id")),
            full_name=u.get("full_name") or "",
            email=u.get("email") or "",
            role=u.get("role") or "customer",
            country=u.get("country"),
            status=u.get("status") or "active",
            created_at=str(u.get("created_at")) if u.get("created_at") else None,
        )
        for u in users
    ]


@router.put("/users/{user_id}/status")
def set_user_status(
    user_id: str,
    payload: AdminUserStatusRequest,
    admin: dict = Depends(require_admin),
) -> dict[str, str]:
    new_status = payload.status.strip().lower()
    if new_status not in ALLOWED_USER_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of: {', '.join(sorted(ALLOWED_USER_STATUSES))}",
        )

    if user_id == admin["user_id"] and new_status == "suspended":
        raise HTTPException(status_code=400, detail="You cannot suspend your own admin account.")

    result = supabase.table("users").update({"status": new_status}).eq("id", user_id).execute()

    if not result.data:
        raise HTTPException(
            status_code=404,
            detail=(
                "User not found, or the 'status' column does not exist yet on the "
                "'users' table. Run this once in Supabase SQL editor: "
                "ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active';"
            ),
        )

    return {"message": f"User status updated to '{new_status}'.", "user_id": user_id, "status": new_status}


# ─── DOMAIN MODERATION ─────────────────────────────────────────

@router.post("/domains/{domain}/freeze", response_model=DomainMutationResponse)
def freeze_domain(
    domain: str,
    payload: AdminFreezeRequest,
    request: Request,
    admin: dict = Depends(require_admin),
) -> DomainMutationResponse:
    service = _service_from_request(request)

    try:
        result = service.freeze_domain(domain=domain, admin_user_id=admin["user_id"], reason=payload.reason)
    except DomainNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DomainAlreadyFrozenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return DomainMutationResponse(
        tx_id=result.tx_id,
        block_hash=result.block_hash,
        chain_height=result.chain_height,
    )


@router.post("/domains/{domain}/unfreeze", response_model=DomainMutationResponse)
def unfreeze_domain(
    domain: str,
    payload: AdminFreezeRequest,
    request: Request,
    admin: dict = Depends(require_admin),
) -> DomainMutationResponse:
    service = _service_from_request(request)

    try:
        result = service.unfreeze_domain(domain=domain, admin_user_id=admin["user_id"], reason=payload.reason)
    except DomainNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DomainAlreadyActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return DomainMutationResponse(
        tx_id=result.tx_id,
        block_hash=result.block_hash,
        chain_height=result.chain_height,
    )


# ─── GLOBAL AUDIT TRAIL ─────────────────────────────────────────

@router.get("/audit", response_model=list[GlobalAuditEvent])
def global_audit_trail(
    request: Request,
    admin: dict = Depends(require_admin),
    limit: int = 200,
) -> list[GlobalAuditEvent]:
    service = _service_from_request(request)
    return [GlobalAuditEvent(**event) for event in service.get_global_audit_trail(limit=limit)]


# ─── ADMIN STATS (drives the admin dashboard overview) ─────────

@router.get("/stats", response_model=AdminStatsResponse)
def admin_stats(request: Request, admin: dict = Depends(require_admin)) -> AdminStatsResponse:
    service = _service_from_request(request)
    domains = service.list_domains()
    frozen_domains = sum(1 for d in domains if d.get("status") == "frozen")

    try:
        users_result = supabase.table("users").select("*").execute()
        users = users_result.data or []
    except Exception:
        users = []

    admin_count = sum(1 for u in users if (u.get("role") or "customer") == "admin")
    customer_count = len(users) - admin_count

    try:
        events_result = supabase.table("audit_logs").select("id").execute()
        total_security_events = len(events_result.data or [])
    except Exception:
        total_security_events = 0

    return AdminStatsResponse(
        total_users=len(users),
        total_domains=len(domains),
        frozen_domains=frozen_domains,
        chain_height=service.ledger.get_chain_height(),
        total_security_events=total_security_events,
        admin_count=admin_count,
        customer_count=customer_count,
    )
