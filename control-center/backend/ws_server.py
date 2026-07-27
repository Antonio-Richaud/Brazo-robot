"""Servidor WebSocket local con publicacion por revision y cierre limpio."""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable
from typing import Any

import websockets


class WebSocketStateServer:
    def __init__(
        self,
        state,
        command_handler: Callable[[dict[str, Any]], bool] | None = None,
        host: str = "127.0.0.1",
        port: int = 8765,
        publish_interval: float = 0.05,
    ):
        self.state = state
        self.command_handler = command_handler
        self.host = host
        self.port = port
        self.publish_interval = publish_interval
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None
        self._ready = threading.Event()

    async def _producer(self, websocket) -> None:
        last_revision = -1
        while True:
            revision = self.state.revision
            if revision != last_revision:
                await websocket.send(json.dumps(self.state.snapshot(), ensure_ascii=False))
                last_revision = revision
            await asyncio.sleep(self.publish_interval)

    async def _consumer(self, websocket) -> None:
        async for message in websocket:
            try:
                data = json.loads(message)
            except (json.JSONDecodeError, TypeError):
                self.state.add_log("[WS] mensaje JSON invalido")
                continue
            if not isinstance(data, dict):
                continue
            if self.command_handler and not self.command_handler(data):
                self.state.add_log(f"[WS] comando rechazado: {data.get('action', '?')}")

    async def _handler(self, websocket) -> None:
        self.state.add_log("[WS] cliente conectado")
        producer = asyncio.create_task(self._producer(websocket))
        consumer = asyncio.create_task(self._consumer(websocket))
        done, pending = await asyncio.wait(
            (producer, consumer), return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            task.exception() if not task.cancelled() else None
        self.state.add_log("[WS] cliente desconectado")

    async def _run_server(self) -> None:
        self._stop_event = asyncio.Event()
        async with websockets.serve(self._handler, self.host, self.port):
            self._ready.set()
            await self._stop_event.wait()

    def _thread_target(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_server())
        finally:
            self._loop.close()

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._thread_target,
            name="robot-websocket",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=2.0):
            raise RuntimeError("El servidor WebSocket no inicio a tiempo.")

    def stop(self) -> None:
        if self._loop and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
