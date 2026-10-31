"""Servidor de reproduccion Jetson exclusivamente de LECTURA en Mac.

Recibe una unica demostracion JSONL completa por stdin (validada previamente
en su totalidad), y la REPRODUCE repetidamente para visualizarla en React.

Seguridad:
- No SSH interno, serial, GPIO, I2C, PWM o procesos de hardware.
- WebSocket SOLO loopback 127.0.0.1:8767 (distinto de backend normal :8765).
- command_handler=None: NINGUN comando entrante modifica el modelo.
- RobotState.mode='monitor' (la interfaz debe bloquear los controles).
- Un flujo invalido no inicia el servidor.
- No es lectura continua de movimientos fisicos; es REPLAY de simulacion Jetson.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Iterable
from typing import Any

from config import SERVO_SPECS
from jetson_telemetry_reader import read_demo_stream, TelemetryValidationError
from robot_state import RobotState
from ws_server import WebSocketStateServer


MONITOR_HOST = "127.0.0.1"
MONITOR_PORT = 8767
REPLAY_INTERVAL_S = 0.1
REPLAY_PAUSE_S = 1.5
RUNTIME_LABEL = "jetson_replay"


def create_monitor_state() -> RobotState:
    """No crea RobotController/SerialManager; solo estado de lectura."""
    state = RobotState()
    state.set_runtime_mode(RUNTIME_LABEL)
    state.set_mode("monitor")
    state.add_log("[JETSON] REPLAY de simulacion validada (NO hardware)")
    return state


def apply_frame(state: RobotState, frame: dict[str, Any]) -> None:
    """Copia un snapshot YA validado al modelo de solo lectura.

    Este adaptador no tiene ninguna via a dispositivos ni serial.
    """
    if state.snapshot()["runtime_mode"] != RUNTIME_LABEL:
        raise RuntimeError("Modo incorrecto para monitor Jetson")
    if state.get_mode() != "monitor":
        raise RuntimeError("El modo de monitor ha cambiado")

    for spec in SERVO_SPECS:
        servo = frame["servos"][spec.name]
        state.update_from_status_line(
            servo_name=spec.name,
            pca_channel=spec.pca_channel,
            current=servo["current"],
            target=servo["target"],
            min_angle=spec.min_angle,
            max_angle=spec.max_angle,
        )


def create_monitor_websocket(state: RobotState) -> WebSocketStateServer:
    """Comandos WebSocket ignorados: el handler no existe."""
    return WebSocketStateServer(
        state=state,
        command_handler=None,
        host=MONITOR_HOST,
        port=MONITOR_PORT,
        publish_interval=0.02,
    )


def replay_frames(
    state: RobotState,
    frames: Iterable[dict[str, Any]],
    sleep=time.sleep,
) -> None:
    """Un recorrido seguro de reproduccion en RAM; sin I/O de red propio."""
    for frame in frames:
        apply_frame(state, frame)
        sleep(REPLAY_INTERVAL_S)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Monitor Mac de replay Jetson simulado, SIN control fisico"
    )
    parser.add_argument(
        "--stdin-demo", action="store_true",
        help="requiere demo JSONL Jetson completa en stdin"
    )
    args = parser.parse_args(argv)
    if not args.stdin_demo:
        parser.error("Solo disponible con --stdin-demo")

    # CRITICO: validar las 13 tramas ANTES de abrir un WebSocket.
    try:
        frames = read_demo_stream(sys.stdin)
    except (TelemetryValidationError, UnicodeError) as exc:
        print(f"MONITOR RECHAZADO: {exc}", file=sys.stderr)
        return 1

    state = create_monitor_state()
    ws = create_monitor_websocket(state)
    try:
        ws.start()
        print(
            f"JETSON_REPLAY_MONITOR_READY ws://{MONITOR_HOST}:{MONITOR_PORT}",
            flush=True,
        )
        print(
            "Modo: replay Jetson matematico / solo lectura / sin motores. "
            "Detener con Ctrl+C.",
            flush=True,
        )
        while True:
            replay_frames(state, frames)
            time.sleep(REPLAY_PAUSE_S)
    except KeyboardInterrupt:
        print("JETSON_REPLAY_MONITOR_STOPPED", flush=True)
        return 0
    finally:
        ws.stop()


if __name__ == "__main__":
    raise SystemExit(main())
