import asyncio
import json
import websockets

async def main():
    uri = "ws://127.0.0.1:8765"
    async with websockets.connect(uri) as ws:
        message = await ws.recv()
        data = json.loads(message)

        print("connected:", data["connected"])
        print("mode:", data["mode"])
        print("base:", data["servos"]["base"])
        print("joystick:", data["joystick"])

asyncio.run(main())
