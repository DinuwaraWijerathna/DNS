from fastapi import APIRouter
from pydantic import BaseModel
from app.services.auth_service import register_user, login_user
from app.services.otp_service import send_verification_otp, verify_otp
from app.core.supabase_client import supabase

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    country: str | None = None
    contact_number: str | None = None
    date_of_birth: str | None = None
    role: str | None = None
    # "role" defaults to "customer". A value of "admin" is only granted if
    # admin_code matches the server-side ADMIN_REGISTRATION_CODE secret -
    # see auth_service.register_user. Without a valid code this silently
    # falls back to "customer".
    admin_code: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class SendOTPRequest(BaseModel):
    email: str
    full_name: str


class VerifyOTPRequest(BaseModel):
    email: str
    otp: str


@router.post("/register")
def register(request: RegisterRequest):
    result = register_user(request.dict())

    # If registration succeeded (no error), auto-send OTP
    if not result.get("error"):
        email = result.get("email", "")
        full_name = result.get("full_name", "User")
        sent, msg = send_verification_otp(email, full_name)
        if sent:
            return {
                "status": "pending_verification",
                "email": email,
                "message": "Account created. A 6-digit OTP has been sent to your email. Please verify to activate your account."
            }
        else:
            # OTP send failed - still created, but let them resend
            return {
                "status": "pending_verification",
                "email": email,
                "message": "Account created but we could not send the verification email. Use 'Resend OTP' to try again.",
                "email_send_failed": True
            }

    return result


@router.post("/login")
def login(request: LoginRequest):
    return login_user(request.email, request.password)


@router.post("/send-otp")
def send_otp(request: SendOTPRequest):
    """Send (or resend) a verification OTP to the user's email."""
    email = (request.email or "").strip().lower()
    full_name = (request.full_name or "User").strip()

    # Make sure this email is actually pending verification
    result = supabase.table("users").select("id, email_verified, full_name").eq("email", email).execute()
    if not result.data:
        return {"error": "No account found with this email."}

    user = result.data[0]
    if user.get("email_verified") is True:
        return {"error": "This account is already verified."}

    actual_name = user.get("full_name") or full_name
    sent, msg = send_verification_otp(email, actual_name)
    if sent:
        return {"message": "Verification code sent to your email."}
    return {"error": msg}


@router.post("/verify-otp")
def verify_email_otp(request: VerifyOTPRequest):
    """Verify OTP and activate the user's account."""
    email = (request.email or "").strip().lower()
    otp = (request.otp or "").strip()

    if not email or not otp:
        return {"error": "Email and OTP are required."}

    if not verify_otp(email, otp):
        return {"error": "Invalid or expired verification code. Please try again."}

    # Activate the account by setting email_verified to True
    update_data = {"email_verified": True}
    update_result = supabase.table("users").update(update_data).eq("email", email).execute()
    if not update_result.data:
        return {"error": "Account not found."}

    return {"message": "Email verified successfully! You can now login.", "verified": True}