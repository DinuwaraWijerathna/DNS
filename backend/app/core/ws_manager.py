from __future__ import annotations

import asyncio
from typing import Any, Optional

from fastapi import WebSocket


class ConnectionManager:
    """Tracks active WebSocket connections and broadcasts JSON messages to all of them."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._connections)

        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)


manager = ConnectionManager()

# The DomainService that triggers broadcasts runs its (synchronous) methods inside
# FastAPI's threadpool - NOT on the main asyncio event loop. To safely schedule an
# async broadcast from that worker thread, we keep a reference to the main loop
# (captured once at startup) and use asyncio.run_coroutine_threadsafe, which is the
# standard-library-sanctioned way to hand work back to a loop from another thread.
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def broadcast_chain_update(payload: dict[str, Any]) -> None:
    """Fire-and-forget broadcast. Safe to call from sync code running in a worker thread."""
    if _main_loop is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(manager.broadcast(payload), _main_loop)
    except RuntimeError:
        pass
