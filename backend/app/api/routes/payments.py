from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_user
from app.core.supabase_client import supabase
from app.services.paypal_service import PayPalError, PayPalService, PLAN_PRICES

router = APIRouter(prefix="/payments", tags=["payments"])


class CreateOrderRequest(BaseModel):
    plan: str


class CaptureOrderRequest(BaseModel):
    order_id: str
    plan: str
    user_email: str | None = None


@router.post("/create-order")
async def create_order(payload: CreateOrderRequest) -> dict:
    if payload.plan not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail="Unknown plan.")

    try:
        service = PayPalService()
        order = await service.create_order(payload.plan)
    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"order_id": order["id"]}


@router.post("/capture-order")
async def capture_order(
    payload: CaptureOrderRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    if payload.plan not in PLAN_PRICES:
        raise HTTPException(status_code=400, detail="Unknown plan.")

    try:
        service = PayPalService()
        result = await service.capture_order(payload.order_id)
    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    status = result.get("status", "UNKNOWN")

    purchase_unit = (result.get("purchase_units") or [{}])[0]
    capture = (purchase_unit.get("payments", {}).get("captures") or [{}])[0]
    amount = capture.get("amount", {}).get("value")
    currency = capture.get("amount", {}).get("currency_code")

    supabase.table("payments").insert(
        {
            "user_email": payload.user_email,
            "plan": payload.plan,
            "amount": amount,
            "currency": currency,
            "paypal_order_id": payload.order_id,
            "status": status,
        }
    ).execute()

    if status != "COMPLETED":
        raise HTTPException(status_code=402, detail="Payment was not completed.")

    # This is the actual "upgrade" - the whole point of paying is that the
    # user's account now carries this plan, so every later request
    # (domain registration limits, feature gates, etc.) can look it up
    # from their JWT-identified user row instead of trusting anything the
    # client claims. Without this line, a completed payment was previously
    # just a log entry with no effect on the account.
    supabase.table("users").update({"plan": payload.plan}).eq(
        "id", current_user["user_id"]
    ).execute()

    return {
        "message": "Payment captured and verified successfully.",
        "order_id": payload.order_id,
        "status": status,
        "amount": amount,
        "currency": currency,
        "plan": payload.plan,
    }
