from __future__ import annotations

import jwt
from fastapi import HTTPException, Request, status

from app.core.config import get_settings

settings = get_settings()


def get_current_user(request: Request) -> dict:
    """Decode and validate the Bearer JWT on the request.

    Raises 401 if the token is missing, malformed, expired, or invalid.
    """
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")

    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected: Bearer <token>",
        )

    token = auth_header.split(" ", 1)[1].strip()

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc

    user_id = payload.get("user_id")
    role = payload.get("role")

    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token.",
        )

    return {"user_id": user_id, "role": role}


def require_admin(request: Request) -> dict:
    """FastAPI dependency: only lets the request through if the JWT belongs to an admin."""
    user = get_current_user(request)

    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this action.",
        )

    return user
