from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from app.cache.redis_client import RedisCacheClient
from app.resolver.dns_adapter import DnsAdapter
from app.services.domain_service import DomainService


class ResolverService:
    def __init__(
        self,
        *,
        domain_service: DomainService,
        cache_client: RedisCacheClient,
        dns_adapter: DnsAdapter,
        cache_ttl_seconds: int = 60,
        metrics_log_size: int = 200,
    ) -> None:
        self.domain_service = domain_service
        self.cache_client = cache_client
        self.dns_adapter = dns_adapter
        self.cache_ttl_seconds = cache_ttl_seconds
        self.total_queries = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_latency_ms = 0.0
        self.query_logs: deque[dict[str, Any]] = deque(maxlen=metrics_log_size)

    def resolve_domain(self, domain: str) -> dict[str, Any]:
        normalized_domain = domain.strip().lower()
        started = perf_counter()
        cache_key = self.cache_client.domain_cache_key(normalized_domain)
        cached = self.cache_client.get_json(cache_key)

        if cached is not None:
            record = self.dns_adapter.format_a_record(
                domain=normalized_domain,
                ip=cached["ip"],
                source="cache",
                ttl_seconds=self.cache_ttl_seconds,
            )
            self._record_query(
                domain=normalized_domain,
                cache_hit=True,
                resolved_ip=record["ip"],
                latency_ms=(perf_counter() - started) * 1000,
            )
            return record

        domain_record = self.domain_service.get_domain(normalized_domain)
        self.cache_client.set_json(cache_key, domain_record, ttl_seconds=self.cache_ttl_seconds)
        record = self.dns_adapter.format_a_record(
            domain=normalized_domain,
            ip=domain_record["ip"],
            source="ledger",
            ttl_seconds=self.cache_ttl_seconds,
        )
        self._record_query(
            domain=normalized_domain,
            cache_hit=False,
            resolved_ip=record["ip"],
            latency_ms=(perf_counter() - started) * 1000,
        )
        return record

    def get_metrics(self) -> dict[str, float | int]:
        hit_rate = (self.cache_hits / self.total_queries) if self.total_queries else 0.0
        avg_latency_ms = (self.total_latency_ms / self.total_queries) if self.total_queries else 0.0
        return {
            "total_queries": self.total_queries,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(hit_rate, 4),
            "average_response_time_ms": round(avg_latency_ms, 3),
            "recent_logs_count": len(self.query_logs),
        }

    def get_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(self.query_logs)[-limit:]

    def _record_query(
        self,
        *,
        domain: str,
        cache_hit: bool,
        resolved_ip: str,
        latency_ms: float,
    ) -> None:
        self.total_queries += 1
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        self.total_latency_ms += latency_ms
        self.query_logs.append(
            {
                "domain": domain,
                "cache_hit": cache_hit,
                "resolved_ip": resolved_ip,
                "response_time_ms": round(latency_ms, 3),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
