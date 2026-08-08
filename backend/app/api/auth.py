from fastapi import APIRouter
from pydantic import BaseModel
from app.services.auth_service import register_user, login_user

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


@router.post("/register")
def register(request: RegisterRequest):
    return register_user(request.dict())


@router.post("/login")
def login(request: LoginRequest):
    return login_user(request.email, request.password)