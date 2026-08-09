from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

from app.core.security import get_current_user
from app.core.supabase_client import supabase
from app.models.schemas import (
    AddTicketReplyRequest,
    CreateSupportTicketRequest,
    SupportTicketReply,
    SupportTicketResponse,
)

router = APIRouter(prefix="/tickets", tags=["support-tickets"])

ALLOWED_STATUSES = {"open", "in_progress", "closed"}
ALLOWED_PRIORITIES = {"low", "normal", "high", "urgent"}


def _fetch_user_row(user_id: str) -> dict[str, Any]:
    result = supabase.table("users").select("*").eq("id", user_id).execute()
    return (result.data or [{}])[0]


def _fetch_ticket_or_404(ticket_id: str) -> dict[str, Any]:
    result = supabase.table("support_tickets").select("*").eq("id", ticket_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Support ticket not found.")
    return result.data[0]


def _assert_can_view_ticket(ticket: dict[str, Any], current_user: dict) -> None:
    if current_user["role"] == "admin":
        return
    if str(ticket.get("user_id")) != str(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="You can only view your own support tickets.")


def _to_ticket_response(ticket: dict[str, Any], include_replies: bool = True) -> SupportTicketResponse:
    owner = _fetch_user_row(str(ticket.get("user_id"))) if ticket.get("user_id") else {}

    replies: list[SupportTicketReply] = []
    if include_replies:
        replies_result = (
            supabase.table("support_ticket_replies")
            .select("*")
            .eq("ticket_id", ticket["id"])
            .execute()
        )
        raw_replies = replies_result.data or []
        raw_replies.sort(key=lambda r: str(r.get("created_at") or ""))

        author_ids = {str(r.get("author_id")) for r in raw_replies if r.get("author_id")}
        authors_by_id = {}
        if author_ids:
            authors_result = supabase.table("users").select("id,full_name,role").in_("id", list(author_ids)).execute()
            for u in authors_result.data or []:
                authors_by_id[str(u.get("id"))] = u

        for r in raw_replies:
            author = authors_by_id.get(str(r.get("author_id")), {})
            replies.append(
                SupportTicketReply(
                    id=str(r.get("id")),
                    ticket_id=str(r.get("ticket_id")),
                    author_id=str(r.get("author_id")) if r.get("author_id") else None,
                    author_name=author.get("full_name"),
                    author_role=author.get("role"),
                    message=r.get("message") or "",
                    created_at=str(r.get("created_at")) if r.get("created_at") else None,
                )
            )

    return SupportTicketResponse(
        ticket_id=str(ticket.get("id")),
        user_id=str(ticket.get("user_id")) if ticket.get("user_id") else None,
        user_name=owner.get("full_name"),
        user_email=owner.get("email"),
        subject=ticket.get("subject") or "",
        message=ticket.get("message") or "",
        status=ticket.get("status") or "open",
        priority=ticket.get("priority") or "normal",
        created_at=str(ticket.get("created_at")) if ticket.get("created_at") else None,
        updated_at=str(ticket.get("updated_at")) if ticket.get("updated_at") else None,
        replies=replies,
    )


@router.post("", response_model=SupportTicketResponse)
def create_ticket(
    payload: CreateSupportTicketRequest,
    current_user: dict = Depends(get_current_user),
) -> SupportTicketResponse:
    subject = payload.subject.strip()
    message = payload.message.strip()
    priority = (payload.priority or "normal").strip().lower()

    if not subject or not message:
        raise HTTPException(status_code=400, detail="Subject and message are required.")
    if priority not in ALLOWED_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Priority must be one of: {', '.join(sorted(ALLOWED_PRIORITIES))}")

    result = (
        supabase.table("support_tickets")
        .insert(
            {
                "user_id": current_user["user_id"],
                "subject": subject,
                "message": message,
                "status": "open",
                "priority": priority,
            }
        )
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=503,
            detail=(
                "Could not create ticket. Make sure the 'support_tickets' table exists "
                "(run supabase_schema.sql in the Supabase SQL editor)."
            ),
        )

    return _to_ticket_response(result.data[0])


@router.get("/mine", response_model=list[SupportTicketResponse])
def list_my_tickets(current_user: dict = Depends(get_current_user)) -> list[SupportTicketResponse]:
    result = supabase.table("support_tickets").select("*").eq("user_id", current_user["user_id"]).execute()
    tickets: list[dict[str, Any]] = result.data or []
    tickets.sort(key=lambda t: str(t.get("created_at") or ""), reverse=True)
    return [_to_ticket_response(t, include_replies=False) for t in tickets]


@router.get("/{ticket_id}", response_model=SupportTicketResponse)
def get_ticket(ticket_id: str, current_user: dict = Depends(get_current_user)) -> SupportTicketResponse:
    ticket = _fetch_ticket_or_404(ticket_id)
    _assert_can_view_ticket(ticket, current_user)
    return _to_ticket_response(ticket)


@router.post("/{ticket_id}/replies", response_model=SupportTicketResponse)
def add_ticket_reply(
    ticket_id: str,
    payload: AddTicketReplyRequest,
    current_user: dict = Depends(get_current_user),
) -> SupportTicketResponse:
    ticket = _fetch_ticket_or_404(ticket_id)
    _assert_can_view_ticket(ticket, current_user)

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Reply message cannot be empty.")

    if ticket.get("status") == "closed" and current_user["role"] != "admin":
        raise HTTPException(status_code=400, detail="This ticket is closed. Only an admin can reopen it.")

    supabase.table("support_ticket_replies").insert(
        {
            "ticket_id": ticket_id,
            "author_id": current_user["user_id"],
            "message": message,
        }
    ).execute()

    # An admin reply nudges an open ticket into "in_progress" automatically.
    update_data: dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}
    if current_user["role"] == "admin" and ticket.get("status") == "open":
        update_data["status"] = "in_progress"

    supabase.table("support_tickets").update(update_data).eq("id", ticket_id).execute()

    return _to_ticket_response(_fetch_ticket_or_404(ticket_id))
