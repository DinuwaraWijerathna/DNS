from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.blockchain.transaction import Transaction


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class Block:
    index: int
    previous_hash: str
    transactions: list[Transaction]
    validator: str
    timestamp: str = field(default_factory=_utc_now)
    nonce: int = 0
    hash: str = ""

    def __post_init__(self) -> None:
        if not self.hash:
            self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        body = {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "validator": self.validator,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "validator": self.validator,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Block:
        return cls(
            index=data["index"],
            previous_hash=data["previous_hash"],
            transactions=[Transaction.from_dict(tx) for tx in data["transactions"]],
            validator=data["validator"],
            timestamp=data["timestamp"],
            nonce=data.get("nonce", 0),
            hash=data["hash"],
        )
