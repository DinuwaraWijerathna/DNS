from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class Transaction:
    tx_type: str
    domain: str
    payload: dict[str, Any]
    owner_public_key: str
    signature: str
    timestamp: str = field(default_factory=_utc_now)
    tx_id: str = ""

    def __post_init__(self) -> None:
        if not self.tx_id:
            self.tx_id = self._compute_tx_id()

    def _compute_tx_id(self) -> str:
        base = {
            "tx_type": self.tx_type,
            "domain": self.domain,
            "payload": self.payload,
            "owner_public_key": self.owner_public_key,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }
        encoded = json.dumps(base, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "tx_type": self.tx_type,
            "domain": self.domain,
            "payload": self.payload,
            "owner_public_key": self.owner_public_key,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Transaction:
        return cls(
            tx_id=data["tx_id"],
            tx_type=data["tx_type"],
            domain=data["domain"],
            payload=data["payload"],
            owner_public_key=data["owner_public_key"],
            signature=data["signature"],
            timestamp=data["timestamp"],
        )
