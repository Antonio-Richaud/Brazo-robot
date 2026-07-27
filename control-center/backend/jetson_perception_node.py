"""Nodo headless para Jetson Nano + RealSense D435i.

Captura y reduce la nube en la Jetson; la Mac recibe solamente puntos 3D
compactos por WebSocket. No ejecuta la interfaz ni controla los servos.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import time

import websockets

from config import PERCEPTION_MAX_POINTS, PERCEPTION_RATE_HZ, REALSENSE_SERIAL
from perception import RealSenseProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nodo RealSense para Jetson Nano")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--serial", default=REALSENSE_SERIAL)
    parser.add_argument("--rate", type=float, default=min(PERCEPTION_RATE_HZ, 8.0))
    parser.add_argument("--max-points", type=int, default=min(PERCEPTION_MAX_POINTS, 1000))
    return parser.parse_args()


async def run(args: argparse.Namespace) -> None:
    clients = set()
    stop_event = asyncio.Event()
    provider = RealSenseProvider(args.serial, args.max_points)

    async def handler(websocket):
        clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            clients.discard(websocket)

    def request_stop() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_stop)
        except NotImplementedError:
            pass

    provider.open()
    interval = 1.0 / max(1.0, args.rate)
    print(f"[JETSON] D435i {args.serial} lista")
    print(f"[JETSON] publicando en ws://{args.host}:{args.port}")
    try:
        async with websockets.serve(handler, args.host, args.port):
            while not stop_event.is_set():
                started = time.monotonic()
                frame = await asyncio.to_thread(provider.capture)
                payload = json.dumps(
                    {
                        "type": "perception",
                        "timestamp": time.time(),
                        "coordinate_frame": frame.coordinate_frame,
                        "calibrated": frame.calibrated,
                        "closest_distance_m": frame.closest_distance_m,
                        "points": frame.points,
                        "obstacles": frame.obstacles,
                    },
                    separators=(",", ":"),
                )
                if clients:
                    await asyncio.gather(
                        *(client.send(payload) for client in tuple(clients)),
                        return_exceptions=True,
                    )
                remaining = interval - (time.monotonic() - started)
                if remaining > 0:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=remaining)
                    except asyncio.TimeoutError:
                        pass
    finally:
        provider.close()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
