from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(request: Request) -> dict[str, int | str]:
    ledger = getattr(request.app.state, "ledger", None)
    chain_height = ledger.get_chain_height() if ledger else 0
    return {"status": "ok", "chain_height": chain_height}
