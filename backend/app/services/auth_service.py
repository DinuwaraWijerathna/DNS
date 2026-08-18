import bcrypt
import jwt
import os
import re
from datetime import datetime, timedelta
from app.core.supabase_client import supabase

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", 24))
# Shared secret required for anyone self-registering an admin account.
# Only people who already know this code (distributed privately by the
# organization) can create an admin account through the public form.
ADMIN_REGISTRATION_CODE = os.getenv("ADMIN_REGISTRATION_CODE")

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def hash_password(password: str):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed: str):
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: str, role: str):
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRES_HOURS)
    }

    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def register_user(data):
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    country = (data.get("country") or "").strip()

    if not full_name:
        return {"error": "Full name is required."}

    if not country:
        return {"error": "Country is required."}

    if not EMAIL_PATTERN.match(email):
        return {"error": "Please enter a valid email address."}

    if len(password) < MIN_PASSWORD_LENGTH:
        return {"error": f"Password must be at least {MIN_PASSWORD_LENGTH} characters."}

    # The client can request "admin", but that request is only honoured if
    # it is accompanied by the correct ADMIN_REGISTRATION_CODE secret.
    # Never trust a bare "role" value coming from the client on its own -
    # that would let anyone grant themselves admin access.
    requested_role = (data.get("role") or "customer").strip().lower()
    admin_code = (data.get("admin_code") or "").strip()

    if requested_role == "admin":
        if not ADMIN_REGISTRATION_CODE or admin_code != ADMIN_REGISTRATION_CODE:
            return {"error": "Invalid admin invite code."}
        role = "admin"
    else:
        role = "customer"

    existing = supabase.table("users") \
        .select("*") \
        .eq("email", email) \
        .execute()

    if existing.data:
        return {"error": "An account with this email already exists."}

    password_hash = hash_password(password)

    insert_data = {
        "full_name": full_name,
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "country": country,
        "contact_number": data.get("contact_number"),
        "date_of_birth": data.get("date_of_birth") or None,
        "email_verified": False,
    }

    result = supabase.table("users") \
        .insert(insert_data) \
        .execute()

    if not result.data:
        return {"error": "Failed to create account. Please try again."}

    user_row = result.data[0]
    return {"user_id": user_row["id"], "email": email, "full_name": full_name}


def login_user(email: str, password: str):
    email = (email or "").strip().lower()

    result = supabase.table("users") \
        .select("*") \
        .eq("email", email) \
        .execute()

    if not result.data:
        return {"error": "Invalid email or password"}

    user = result.data[0]

    if not verify_password(password, user["password_hash"]):
        return {"error": "Invalid email or password"}

    status = user.get("status") or "active"

    if status == "suspended":
        return {"error": "This account has been suspended by an administrator. Please contact support."}

    email_verified = user.get("email_verified")
    if email_verified is False or status == "pending_verification":
        return {"error": "EMAIL_NOT_VERIFIED", "email": email}


    token = create_token(user["id"], user["role"])

    return {
        "token": token,
        "user": {
            "user_id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"]
        }
    }