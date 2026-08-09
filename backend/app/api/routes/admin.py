from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.security import require_admin
from app.core.supabase_client import supabase
from app.models.schemas import (
    AdminActivityLogResponse,
    AdminFreezeRequest,
    AdminPaymentResponse,
    AdminPaymentSummaryResponse,
    AdminStatsResponse,
    AdminUserResponse,
    AdminUserStatusRequest,
    DomainMutationResponse,
    GlobalAuditEvent,
    SupportTicketResponse,
    UpdateSupportTicketRequest,
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


def _log_admin_activity(
    admin: dict,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Best-effort write to admin_activity_log. Never blocks the main request."""
    try:
        supabase.table("admin_activity_log").insert(
            {
                "admin_id": admin.get("user_id"),
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "details": details or {},
            }
        ).execute()
    except Exception:
        # Table may not exist yet, or Supabase may be briefly unavailable.
        # Activity logging must never break the admin action itself.
        pass


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

    _log_admin_activity(
        admin,
        action="USER_STATUS_CHANGE",
        target_type="user",
        target_id=user_id,
        details={"new_status": new_status},
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

    _log_admin_activity(
        admin,
        action="DOMAIN_FREEZE",
        target_type="domain",
        target_id=domain,
        details={"reason": payload.reason, "tx_id": result.tx_id},
    )

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

    _log_admin_activity(
        admin,
        action="DOMAIN_UNFREEZE",
        target_type="domain",
        target_id=domain,
        details={"reason": payload.reason, "tx_id": result.tx_id},
    )

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


# ─── ADMIN ACTIVITY LOG ─────────────────────────────────────────

@router.get("/activity", response_model=list[AdminActivityLogResponse])
def admin_activity_log(
    admin: dict = Depends(require_admin),
    admin_id: str | None = None,
    action: str | None = None,
    limit: int = 200,
) -> list[AdminActivityLogResponse]:
    query = supabase.table("admin_activity_log").select("*")
    if admin_id:
        query = query.eq("admin_id", admin_id)
    if action:
        query = query.eq("action", action.upper())

    try:
        result = query.execute()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "admin_activity_log table not found. Run supabase_schema.sql "
                "(admin_activity_log section) in the Supabase SQL editor."
            ),
        ) from exc

    logs: list[dict[str, Any]] = result.data or []
    logs.sort(key=lambda entry: str(entry.get("created_at") or ""), reverse=True)
    logs = logs[:limit]

    admin_ids = {str(entry.get("admin_id")) for entry in logs if entry.get("admin_id")}
    admins_by_id: dict[str, dict[str, Any]] = {}
    if admin_ids:
        users_result = supabase.table("users").select("id,full_name,email").in_("id", list(admin_ids)).execute()
        for u in users_result.data or []:
            admins_by_id[str(u.get("id"))] = u

    return [
        AdminActivityLogResponse(
            id=str(entry.get("id")),
            admin_id=str(entry.get("admin_id")) if entry.get("admin_id") else None,
            admin_name=admins_by_id.get(str(entry.get("admin_id")), {}).get("full_name"),
            admin_email=admins_by_id.get(str(entry.get("admin_id")), {}).get("email"),
            action=entry.get("action") or "",
            target_type=entry.get("target_type"),
            target_id=entry.get("target_id"),
            details=entry.get("details") or {},
            created_at=str(entry.get("created_at")) if entry.get("created_at") else None,
        )
        for entry in logs
    ]


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


# ─── PAYMENT HISTORY (admin-only view across every customer) ───

@router.get("/payments", response_model=list[AdminPaymentResponse])
def list_payments(
    admin: dict = Depends(require_admin),
    status_filter: str | None = None,
    plan: str | None = None,
    limit: int = 200,
) -> list[AdminPaymentResponse]:
    query = supabase.table("payments").select("*")
    if status_filter:
        query = query.eq("status", status_filter.upper())
    if plan:
        query = query.eq("plan", plan)

    result = query.execute()
    payments: list[dict[str, Any]] = result.data or []
    payments.sort(key=lambda p: str(p.get("created_at") or ""), reverse=True)

    return [
        AdminPaymentResponse(
            payment_id=str(p.get("id")),
            user_email=p.get("user_email"),
            plan=p.get("plan"),
            amount=str(p.get("amount")) if p.get("amount") is not None else None,
            currency=p.get("currency"),
            paypal_order_id=p.get("paypal_order_id"),
            status=p.get("status"),
            created_at=str(p.get("created_at")) if p.get("created_at") else None,
        )
        for p in payments[:limit]
    ]


@router.get("/payments/summary", response_model=AdminPaymentSummaryResponse)
def payments_summary(admin: dict = Depends(require_admin)) -> AdminPaymentSummaryResponse:
    result = supabase.table("payments").select("*").execute()
    payments: list[dict[str, Any]] = result.data or []

    completed = [p for p in payments if (p.get("status") or "").upper() == "COMPLETED"]

    revenue_by_currency: dict[str, float] = {}
    revenue_by_plan: dict[str, float] = {}
    total_revenue = 0.0

    for p in completed:
        try:
            amount = float(p.get("amount") or 0)
        except (TypeError, ValueError):
            continue

        currency = p.get("currency") or "UNKNOWN"
        plan = p.get("plan") or "unknown"

        total_revenue += amount
        revenue_by_currency[currency] = revenue_by_currency.get(currency, 0.0) + amount
        revenue_by_plan[plan] = revenue_by_plan.get(plan, 0.0) + amount

    return AdminPaymentSummaryResponse(
        total_payments=len(payments),
        completed_payments=len(completed),
        total_revenue=round(total_revenue, 2),
        revenue_by_currency={k: round(v, 2) for k, v in revenue_by_currency.items()},
        revenue_by_plan={k: round(v, 2) for k, v in revenue_by_plan.items()},
    )


# ─── SUPPORT TICKETS (admin view across every customer) ────────

@router.get("/tickets", response_model=list[SupportTicketResponse])
def admin_list_tickets(
    admin: dict = Depends(require_admin),
    status_filter: str | None = None,
    priority: str | None = None,
    limit: int = 200,
) -> list[SupportTicketResponse]:
    from app.api.routes.tickets import _to_ticket_response  # local import avoids a circular import at module load time

    query = supabase.table("support_tickets").select("*")
    if status_filter:
        query = query.eq("status", status_filter.lower())
    if priority:
        query = query.eq("priority", priority.lower())

    result = query.execute()
    tickets: list[dict[str, Any]] = result.data or []
    tickets.sort(key=lambda t: str(t.get("created_at") or ""), reverse=True)

    return [_to_ticket_response(t, include_replies=False) for t in tickets[:limit]]


@router.put("/tickets/{ticket_id}", response_model=SupportTicketResponse)
def admin_update_ticket(
    ticket_id: str,
    payload: UpdateSupportTicketRequest,
    admin: dict = Depends(require_admin),
) -> SupportTicketResponse:
    from app.api.routes.tickets import ALLOWED_PRIORITIES, ALLOWED_STATUSES, _fetch_ticket_or_404, _to_ticket_response

    _fetch_ticket_or_404(ticket_id)  # 404s early if the ticket doesn't exist

    update_data: dict[str, Any] = {}
    if payload.status is not None:
        new_status = payload.status.strip().lower()
        if new_status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail=f"Status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}")
        update_data["status"] = new_status
    if payload.priority is not None:
        new_priority = payload.priority.strip().lower()
        if new_priority not in ALLOWED_PRIORITIES:
            raise HTTPException(status_code=400, detail=f"Priority must be one of: {', '.join(sorted(ALLOWED_PRIORITIES))}")
        update_data["priority"] = new_priority

    if not update_data:
        raise HTTPException(status_code=400, detail="Provide at least a status or priority to update.")

    from datetime import datetime

    update_data["updated_at"] = datetime.utcnow().isoformat()
    result = supabase.table("support_tickets").update(update_data).eq("id", ticket_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Support ticket not found.")

    _log_admin_activity(
        admin,
        action="TICKET_UPDATE",
        target_type="support_ticket",
        target_id=ticket_id,
        details=update_data,
    )

    return _to_ticket_response(result.data[0])
