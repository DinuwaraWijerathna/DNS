from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.ws_manager import manager

router = APIRouter(tags=["Realtime"])


@router.websocket("/ws/chain")
async def chain_updates(websocket: WebSocket) -> None:
    """Live feed of blockchain/domain events (register, update, transfer, freeze, ...).

    Clients don't need to send anything - this is a push-only feed. We still read
    from the socket in a loop so the connection is correctly detected as closed
    (and cleaned up) when the client disconnects.
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
