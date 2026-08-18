from __future__ import annotations

import os
import json
from datetime import datetime, timedelta
from app.services.email_service import generate_otp, send_otp_email

OTP_EXPIRY_MINUTES = 10

# ─── Try Redis first, fall back to in-memory dict ─────────────
try:
    import redis as redis_lib
    _redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _r = redis_lib.from_url(_redis_url, decode_responses=True)
    _r.ping()
    _USE_REDIS = True
except Exception:
    _r = None
    _USE_REDIS = False

# In-memory fallback
_otp_store: dict[str, dict] = {}


def _otp_key(email: str) -> str:
    return f"bdns:otp:{email.strip().lower()}"


def store_otp(email: str, otp: str) -> None:
    """Store OTP for the given email with a TTL."""
    email = email.strip().lower()
    expires_at = (datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()
    payload = json.dumps({"otp": otp, "expires_at": expires_at})

    if _USE_REDIS and _r:
        _r.setex(_otp_key(email), OTP_EXPIRY_MINUTES * 60, payload)
    else:
        _otp_store[email] = {"otp": otp, "expires_at": expires_at}


def verify_otp(email: str, otp: str) -> bool:
    """Check OTP for given email. Returns True if correct and not expired."""
    email = email.strip().lower()

    if _USE_REDIS and _r:
        raw = _r.get(_otp_key(email))
        if not raw:
            return False
        data = json.loads(raw)
    else:
        data = _otp_store.get(email)
        if not data:
            return False

    expires_at = datetime.fromisoformat(data["expires_at"])
    if datetime.utcnow() > expires_at:
        # Expired - delete it
        delete_otp(email)
        return False

    if data["otp"] != otp.strip():
        return False

    # Valid! Delete it so it can't be reused
    delete_otp(email)
    return True


def delete_otp(email: str) -> None:
    email = email.strip().lower()
    if _USE_REDIS and _r:
        _r.delete(_otp_key(email))
    else:
        _otp_store.pop(email, None)


def send_verification_otp(email: str, full_name: str) -> tuple[bool, str]:
    """
    Generate OTP, store it, and send via email.
    Returns (success: bool, message: str).
    """
    otp = generate_otp(6)
    store_otp(email, otp)
    sent = send_otp_email(email, full_name, otp)
    if sent:
        return True, "OTP sent successfully to your Gmail."
    else:
        # Keep OTP stored in Redis/memory so verification is still possible
        return False, "OTP generated. (Gmail SMTP delivery pending configuration in backend/.env)"

