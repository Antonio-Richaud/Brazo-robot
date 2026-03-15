import asyncio
import json
import threading
from typing import Callable, Any

import websockets


class WebSocketStateServer:
    def __init__(
        self,
        state,
        command_handler: Callable[[dict[str, Any]], None] | None = None,
        host: str = "127.0.0.1",
        port: int = 8765,
        publish_interval: float = 0.10,
    ):
        self.state = state
        self.command_handler = command_handler
        self.host = host
        self.port = port
        self.publish_interval = publish_interval

        self._thread = None
        self._loop = None
        self._stop_future = None

    async def _producer(self, websocket):
        last_payload = None

        while True:
            snapshot = self.state.snapshot()
            payload = json.dumps(snapshot, ensure_ascii=False)

            if payload != last_payload:
                await websocket.send(payload)
                last_payload = payload

            await asyncio.sleep(self.publish_interval)

    async def _consumer(self, websocket):
        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            if self.command_handler:
                try:
                    self.command_handler(data)
                except Exception as e:
                    print(f"[WS COMMAND ERROR] {e}")

    async def _handler(self, websocket):
        print("[WS] cliente conectado")

        producer_task = asyncio.create_task(self._producer(websocket))
        consumer_task = asyncio.create_task(self._consumer(websocket))

        done, pending = await asyncio.wait(
            [producer_task, consumer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        print("[WS] cliente desconectado")

    async def _run_server(self):
        async with websockets.serve(self._handler, self.host, self.port):
            print(f"[WS] servidor en ws://{self.host}:{self.port}")
            self._stop_future = self._loop.create_future()
            await self._stop_future

    def _thread_target(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._run_server())
        self._loop.close()

    def start(self):
        self._thread = threading.Thread(target=self._thread_target, daemon=True)
        self._thread.start()

    def stop(self):
        if self._loop and self._stop_future and not self._stop_future.done():
            self._loop.call_soon_threadsafe(self._stop_future.set_result, True)
        if self._thread:
            self._thread.join(timeout=1.0)
