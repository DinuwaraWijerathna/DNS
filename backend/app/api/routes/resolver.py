from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.models.schemas import ResolveResponse, ResolverMetricsResponse, ResolverQueryLogEntry
from app.services.domain_service import DomainNotFoundError

router = APIRouter(prefix="/resolver", tags=["resolver"])


def _resolver_service_from_request(request: Request):
    resolver_service = getattr(request.app.state, "resolver_service", None)
    if resolver_service is None:
        raise HTTPException(status_code=503, detail="Resolver service is not initialized.")
    return resolver_service


@router.get("/metrics/summary", response_model=ResolverMetricsResponse)
def resolver_metrics(request: Request) -> ResolverMetricsResponse:
    resolver_service = _resolver_service_from_request(request)
    return ResolverMetricsResponse(**resolver_service.get_metrics())


@router.get("/logs/recent", response_model=list[ResolverQueryLogEntry])
def resolver_logs(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[ResolverQueryLogEntry]:
    resolver_service = _resolver_service_from_request(request)
    return [ResolverQueryLogEntry(**entry) for entry in resolver_service.get_logs(limit)]


@router.get("/{domain}", response_model=ResolveResponse)
def resolve_domain(domain: str, request: Request) -> ResolveResponse:
    resolver_service = _resolver_service_from_request(request)
    try:
        result = resolver_service.resolve_domain(domain)
    except DomainNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResolveResponse(**result)
