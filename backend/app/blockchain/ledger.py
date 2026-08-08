from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.blockchain.block import Block
from app.blockchain.consensus_poa import PoAConsensus
from app.blockchain.transaction import Transaction


class Ledger:
    def __init__(self, consensus: PoAConsensus, storage_path: str) -> None:
        self.consensus = consensus
        self.storage_path = Path(storage_path)
        self.chain: list[Block] = []
        self.pending_transactions: list[Transaction] = []

    def initialize(self) -> None:
        if self.storage_path.exists():
            self.load()
        else:
            self.create_genesis_block()
            self.save()
        if not self.is_chain_valid():
            raise ValueError("Persisted chain is invalid.")

    def create_genesis_block(self) -> None:
        genesis_tx = Transaction(
            tx_type="genesis",
            domain="bdns.genesis",
            payload={"message": "BDNS chain initialized"},
            owner_public_key="system",
            signature="genesis-signature",
        )
        genesis_block = Block(
            index=0,
            previous_hash="0",
            transactions=[genesis_tx],
            validator="genesis",
        )
        self.chain = [genesis_block]

    def add_transaction(self, tx: Transaction) -> str:
        self.pending_transactions.append(tx)
        return tx.tx_id

    def commit_pending_transactions(self, validator: str | None = None) -> Block:
        if not self.pending_transactions:
            raise ValueError("No pending transactions to commit.")
        selected_validator = validator or self.consensus.select_validator(len(self.chain))
        if not self.consensus.is_validator_authorized(selected_validator):
            raise ValueError("Validator is not authorized.")

        previous_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            previous_hash=previous_block.hash,
            transactions=list(self.pending_transactions),
            validator=selected_validator,
        )
        self.chain.append(new_block)
        self.pending_transactions.clear()
        self.save()
        return new_block

    def get_chain_height(self) -> int:
        return len(self.chain)

    def is_chain_valid(self) -> bool:
        if not self.chain:
            return False

        for i, block in enumerate(self.chain):
            computed_hash = block.compute_hash()
            if block.hash != computed_hash:
                return False

            if i == 0:
                if block.previous_hash != "0":
                    return False
                if not self.consensus.validate_block(block, is_genesis=True):
                    return False
                continue

            previous = self.chain[i - 1]
            if block.previous_hash != previous.hash:
                return False
            if block.index != i:
                return False
            if not self.consensus.validate_block(block):
                return False

        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain": [block.to_dict() for block in self.chain],
            "pending_transactions": [tx.to_dict() for tx in self.pending_transactions],
        }

    def save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def load(self) -> None:
        raw_data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        self.chain = [Block.from_dict(item) for item in raw_data.get("chain", [])]
        self.pending_transactions = [
            Transaction.from_dict(item) for item in raw_data.get("pending_transactions", [])
        ]

        if not self.chain:
            self.create_genesis_block()
