from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.blockchain.ledger import Ledger
from app.blockchain.transaction import Transaction

router = APIRouter(prefix="/chain", tags=["chain"])


class SubmitTransactionRequest(BaseModel):
    tx_type: str = Field(..., examples=["register"])
    domain: str = Field(..., examples=["example.bd"])
    payload: dict[str, Any]
    owner_public_key: str
    signature: str


class CommitRequest(BaseModel):
    validator: str | None = None


def _ledger_from_request(request: Request) -> Ledger:
    ledger = getattr(request.app.state, "ledger", None)
    if ledger is None:
        raise HTTPException(status_code=503, detail="Ledger is not initialized.")
    return ledger


@router.get("")
def get_chain(request: Request) -> dict[str, Any]:
    ledger = _ledger_from_request(request)
    return ledger.to_dict()


@router.get("/validate")
def validate_chain(request: Request) -> dict[str, bool]:
    ledger = _ledger_from_request(request)
    return {"is_valid": ledger.is_chain_valid()}


@router.post("/transactions")
def submit_transaction(payload: SubmitTransactionRequest, request: Request) -> dict[str, str]:
    ledger = _ledger_from_request(request)
    tx = Transaction(
        tx_type=payload.tx_type,
        domain=payload.domain,
        payload=payload.payload,
        owner_public_key=payload.owner_public_key,
        signature=payload.signature,
    )
    tx_id = ledger.add_transaction(tx)
    ledger.save()
    return {"tx_id": tx_id}


@router.post("/commit")
def commit_block(payload: CommitRequest, request: Request) -> dict[str, Any]:
    ledger = _ledger_from_request(request)
    try:
        block = ledger.commit_pending_transactions(validator=payload.validator)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"block": block.to_dict(), "chain_height": ledger.get_chain_height()}
