"""Punto de entrada del Control Center.

Ejemplos:
    python main.py --mode simulation --perception simulated
    python main.py --mode hardware --perception off
    python main.py --mode hardware --perception realsense --no-joystick
"""

from __future__ import annotations

import argparse
import time

from config import (
    LOOP_SLEEP,
    REALSENSE_SERIAL,
    PERCEPTION_REMOTE_URL,
    SERIAL_PORT,
    WS_HOST,
    WS_PORT,
    WS_PUBLISH_INTERVAL,
)
from controller import RobotController
from joystick_manager import JoystickManager
from perception import PerceptionWorker
from robot_state import RobotState
from serial_manager import SerialManager
from ws_server import WebSocketStateServer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backend local del brazo robot")
    parser.add_argument(
        "--mode",
        choices=("hardware", "simulation"),
        default="hardware",
        help="Usa el ESP32 real o un movimiento simulado para desarrollar sin hardware.",
    )
    parser.add_argument(
        "--serial-port",
        default=SERIAL_PORT,
        help="Puerto del ESP32; si se omite se intenta detectar automaticamente.",
    )
    parser.add_argument("--no-joystick", action="store_true")
    parser.add_argument(
        "--perception",
        choices=("off", "simulated", "realsense", "remote"),
        default="off",
    )
    parser.add_argument("--realsense-serial", default=REALSENSE_SERIAL)
    parser.add_argument("--perception-url", default=PERCEPTION_REMOTE_URL)
    return parser.parse_args()


def run(args: argparse.Namespace) -> None:
    state = RobotState()
    state.set_runtime_mode(args.mode)
    simulation = args.mode == "simulation"
    controller = RobotController(state=state, simulation=simulation)
    serial_manager = None
    joystick_manager = None
    perception_worker = PerceptionWorker(
        state=state,
        source=args.perception,
        serial=args.realsense_serial,
        remote_url=args.perception_url,
    )
    ws_server = WebSocketStateServer(
        state=state,
        command_handler=controller.handle_command,
        host=WS_HOST,
        port=WS_PORT,
        publish_interval=WS_PUBLISH_INTERVAL,
    )

    try:
        if simulation:
            state.add_log("[RUNTIME] simulacion de brazo activa")
        else:
            serial_manager = SerialManager(
                state=state,
                port=args.serial_port,
                event_handler=controller.handle_protocol_event,
            )
            controller.serial_manager = serial_manager
            try:
                port = serial_manager.connect()
                state.add_log(f"[RUNTIME] ESP32 listo en {port}")
            except Exception as exc:
                # La UI permanece disponible para diagnostico aunque falte el ESP32.
                state.set_error(str(exc))
                state.add_log(f"[RUNTIME] ESP32 no disponible: {exc}")

        if not args.no_joystick:
            try:
                joystick_manager = JoystickManager(
                    state=state,
                    action_handler=controller.handle_command,
                )
                controller.attach_joystick(joystick_manager)
            except Exception as exc:
                state.add_log(f"[JOYSTICK] no disponible: {exc}")

        perception_worker.start()
        ws_server.start()
        state.add_log(f"[WS] ws://{WS_HOST}:{WS_PORT}")

        last_loop = time.monotonic()
        while True:
            now = time.monotonic()
            dt = now - last_loop
            last_loop = now
            if joystick_manager:
                try:
                    joystick_manager.tick(dt)
                except Exception as exc:
                    state.add_log(f"[JOYSTICK ERROR] {exc}")
                    joystick_manager.close()
                    joystick_manager = None
                    controller.joystick_manager = None
            controller.tick(now)
            time.sleep(LOOP_SLEEP)

    except KeyboardInterrupt:
        state.add_log("[RUNTIME] cierre solicitado")
    finally:
        perception_worker.stop()
        ws_server.stop()
        if joystick_manager:
            joystick_manager.close()
        if serial_manager:
            serial_manager.disconnect()


if __name__ == "__main__":
    run(parse_args())
