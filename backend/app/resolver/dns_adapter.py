from __future__ import annotations

from typing import Any


class DnsAdapter:
    def format_a_record(
        self,
        *,
        domain: str,
        ip: str,
        source: str,
        ttl_seconds: int,
    ) -> dict[str, Any]:
        return {
            "domain": domain,
            "record_type": "A",
            "ip": ip,
            "source": source,
            "ttl_seconds": ttl_seconds,
        }
