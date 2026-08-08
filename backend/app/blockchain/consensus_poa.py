from __future__ import annotations

from app.blockchain.block import Block


class PoAConsensus:
    def __init__(self, authorized_validators: list[str]) -> None:
        if not authorized_validators:
            raise ValueError("At least one authorized validator is required.")
        self.authorized_validators = set(authorized_validators)
        self._ordered_validators = sorted(self.authorized_validators)

    def is_validator_authorized(self, validator: str) -> bool:
        return validator in self.authorized_validators

    def validate_block(self, block: Block, is_genesis: bool = False) -> bool:
        if is_genesis:
            return True
        return self.is_validator_authorized(block.validator)

    def select_validator(self, block_height: int) -> str:
        idx = block_height % len(self._ordered_validators)
        return self._ordered_validators[idx]
