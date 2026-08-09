from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RegisterDomainRequest(BaseModel):
    domain: str = Field(..., examples=["example.bd"])
    ip: str = Field(..., examples=["203.0.113.10"])
    owner_public_key: str
    signature: str


class UpdateDomainRequest(BaseModel):
    ip: str = Field(..., examples=["203.0.113.20"])
    owner_public_key: str
    signature: str


class TransferDomainRequest(BaseModel):
    new_owner_public_key: str
    owner_public_key: str
    signature: str


class DomainRecordResponse(BaseModel):
    domain: str
    ip: str
    owner_public_key: str
    updated_at: str
    status: str = "active"


class DomainMutationResponse(BaseModel):
    tx_id: str
    block_hash: str
    chain_height: int


class DomainAuditEvent(BaseModel):
    tx_id: str
    tx_type: str
    domain: str
    payload: dict[str, Any]
    owner_public_key: str
    signature: str
    timestamp: str
    block_index: int
    block_hash: str
    validator: str
    committed_at: datetime


class ResolveResponse(BaseModel):
    domain: str
    record_type: str
    ip: str
    source: str
    ttl_seconds: int


class ResolverMetricsResponse(BaseModel):
    total_queries: int
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float
    average_response_time_ms: float
    recent_logs_count: int


class ResolverQueryLogEntry(BaseModel):
    domain: str
    cache_hit: bool
    resolved_ip: str
    response_time_ms: float
    timestamp: str


class GenerateKeypairResponse(BaseModel):
    private_key: str
    public_key: str


class SignPayloadRequest(BaseModel):
    private_key: str
    tx_type: str
    domain: str
    payload: dict[str, Any]


class SignPayloadResponse(BaseModel):
    owner_public_key: str
    signature: str
    normalized_domain: str


# ─── ADMIN ──────────────────────────────────────────────────

class AdminFreezeRequest(BaseModel):
    reason: str | None = Field(default=None, examples=["Suspected phishing activity"])


class GlobalAuditEvent(BaseModel):
    tx_id: str
    tx_type: str
    domain: str
    payload: dict[str, Any]
    owner_public_key: str
    timestamp: str
    block_index: int
    block_hash: str
    validator: str


class AdminUserResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: str
    country: str | None = None
    status: str = "active"
    created_at: str | None = None


class AdminUserStatusRequest(BaseModel):
    status: str = Field(..., examples=["suspended"])


class AdminStatsResponse(BaseModel):
    total_users: int
    total_domains: int
    frozen_domains: int
    chain_height: int
    total_security_events: int
    admin_count: int
    customer_count: int


# ─── ADMIN ACTIVITY LOG ──────────────────────────────────────

class AdminActivityLogResponse(BaseModel):
    id: str
    admin_id: str | None = None
    admin_name: str | None = None
    admin_email: str | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    details: dict[str, Any] | None = None
    created_at: str | None = None


# ─── ADMIN PAYMENT HISTORY ──────────────────────────────────

class AdminPaymentResponse(BaseModel):
    payment_id: str
    user_email: str | None = None
    plan: str | None = None
    amount: str | None = None
    currency: str | None = None
    paypal_order_id: str | None = None
    status: str | None = None
    created_at: str | None = None


class AdminPaymentSummaryResponse(BaseModel):
    total_payments: int
    completed_payments: int
    total_revenue: float
    revenue_by_currency: dict[str, float]
    revenue_by_plan: dict[str, float]


# ─── CUSTOMER / ADMIN "MY PROFILE" ─────────────────────────

class UserProfileResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: str
    country: str | None = None
    contact_number: str | None = None
    date_of_birth: str | None = None
    status: str = "active"
    created_at: str | None = None
    plan: str | None = None
    domain_limit: int | None = None
    domains_used: int = 0


class UpdateProfileRequest(BaseModel):
    full_name: str
    country: str | None = None
    contact_number: str | None = None
    date_of_birth: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ─── SUPPORT TICKETS ─────────────────────────────────────────

class CreateSupportTicketRequest(BaseModel):
    subject: str = Field(..., examples=["Cannot update my domain's IP address"])
    message: str = Field(..., examples=["I keep getting a signature error when I try to update example.bd"])
    priority: str = Field(default="normal", examples=["normal"])


class UpdateSupportTicketRequest(BaseModel):
    status: str | None = Field(default=None, examples=["in_progress"])
    priority: str | None = Field(default=None, examples=["high"])


class AddTicketReplyRequest(BaseModel):
    message: str = Field(..., examples=["Thanks for the details — please try re-signing with your latest key."])


class SupportTicketReply(BaseModel):
    id: str
    ticket_id: str
    author_id: str | None = None
    author_name: str | None = None
    author_role: str | None = None
    message: str
    created_at: str | None = None


class SupportTicketResponse(BaseModel):
    ticket_id: str
    user_id: str | None = None
    user_name: str | None = None
    user_email: str | None = None
    subject: str
    message: str
    status: str = "open"
    priority: str = "normal"
    created_at: str | None = None
    updated_at: str | None = None
    replies: list[SupportTicketReply] = Field(default_factory=list)
