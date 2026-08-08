from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.core.supabase_client import supabase
from app.models.schemas import (
    ChangePasswordRequest,
    UpdateProfileRequest,
    UserProfileResponse,
)
from app.services.auth_service import MIN_PASSWORD_LENGTH, hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Profile"])


def _fetch_user_row(user_id: str) -> dict:
    result = supabase.table("users").select("*").eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found.")
    return result.data[0]


def _to_profile_response(user: dict) -> UserProfileResponse:
    return UserProfileResponse(
        user_id=str(user.get("id")),
        full_name=user.get("full_name") or "",
        email=user.get("email") or "",
        role=user.get("role") or "customer",
        country=user.get("country"),
        contact_number=user.get("contact_number"),
        date_of_birth=str(user.get("date_of_birth")) if user.get("date_of_birth") else None,
        status=user.get("status") or "active",
        created_at=str(user.get("created_at")) if user.get("created_at") else None,
    )


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(current_user: dict = Depends(get_current_user)) -> UserProfileResponse:
    """Return the logged-in customer's (or admin's) own profile details."""
    user = _fetch_user_row(current_user["user_id"])
    return _to_profile_response(user)


@router.put("/me", response_model=UserProfileResponse)
def update_my_profile(
    payload: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
) -> UserProfileResponse:
    """Let the logged-in user update their own personal details."""
    full_name = (payload.full_name or "").strip()
    if not full_name:
        raise HTTPException(status_code=400, detail="Full name is required.")

    update_data = {
        "full_name": full_name,
        "country": (payload.country or "").strip() or None,
        "contact_number": (payload.contact_number or "").strip() or None,
        "date_of_birth": payload.date_of_birth or None,
    }

    result = (
        supabase.table("users")
        .update(update_data)
        .eq("id", current_user["user_id"])
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="User not found.")

    return _to_profile_response(result.data[0])


@router.put("/me/password")
def change_my_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
) -> dict[str, str]:
    """Let the logged-in user change their own password."""
    if len(payload.new_password or "") < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"New password must be at least {MIN_PASSWORD_LENGTH} characters.",
        )

    user = _fetch_user_row(current_user["user_id"])

    if not verify_password(payload.current_password or "", user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    new_hash = hash_password(payload.new_password)
    supabase.table("users").update({"password_hash": new_hash}).eq(
        "id", current_user["user_id"]
    ).execute()

    return {"message": "Password updated successfully."}
