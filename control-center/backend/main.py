import time

from config import LOOP_SLEEP, SEND_INTERVAL, STATUS_POLL_INTERVAL, SERIAL_PORT, HOME, LIMITS
from joystick_manager import JoystickManager
from robot_state import RobotState
from serial_manager import SerialManager
from ws_server import WebSocketStateServer


def clamp(value, low, high):
    return max(low, min(high, value))


def main():
    state = RobotState()
    serial_manager = SerialManager(state=state, port=SERIAL_PORT)
    joystick_manager = None
    ws_server = None

    try:
        serial_manager.connect()
        joystick_manager = JoystickManager(state=state, serial_manager=serial_manager)

        def handle_ws_command(data: dict):
            action = data.get("action")

            if action == "home":
                serial_manager.send("home")
                joystick_manager.targets = {k: float(v) for k, v in HOME.items()}
                joystick_manager.manual_enabled = True
                joystick_manager.force_sync_targets()
                state.set_mode("manual")
                return

            if action == "saludo":
                serial_manager.send("saludo")
                joystick_manager.manual_enabled = False
                state.set_mode("saludo")
                return

            if action == "stop":
                serial_manager.send("stop")
                joystick_manager.targets = {k: float(v) for k, v in HOME.items()}
                joystick_manager.manual_enabled = True
                joystick_manager.force_sync_targets()
                state.set_mode("manual")
                return

            if action == "set_servo":
                servo_id = int(data.get("servo_id"))
                angle = float(data.get("angle"))

                if servo_id not in joystick_manager.targets:
                    return

                low, high = LIMITS[servo_id]
                angle = clamp(angle, low, high)

                joystick_manager.targets[servo_id] = angle
                joystick_manager.manual_enabled = True
                joystick_manager.force_sync_targets()
                state.update_servo_target(servo_id, int(round(angle)))
                return

ws_server = WebSocketStateServer(
    state=state,
    command_handler=handle_ws_command,
    host="127.0.0.1",
    port=8765,
    publish_interval=0.03,
)
        ws_server.start()

        last_loop = time.time()
        last_send = 0.0
        last_status_poll = 0.0

        print("\n[BACKEND] Control center backend corriendo.")
        print("[BACKEND] WebSocket listo en ws://127.0.0.1:8765")
        print("[BACKEND] Presiona Ctrl+C o el boton rapido 4 para salir.\n")

        while True:
            now = time.time()
            dt = now - last_loop
            last_loop = now

            joystick_manager.tick(dt)

            if joystick_manager.manual_enabled and (now - last_send >= SEND_INTERVAL):
                for sid in range(1, 7):
                    angle = int(round(joystick_manager.targets[sid]))
                    if joystick_manager.last_sent[sid] != angle:
                        serial_manager.send(f"s {sid} {angle}")
                        joystick_manager.last_sent[sid] = angle
                        state.update_servo_target(sid, angle)
                last_send = now

            if now - last_status_poll >= STATUS_POLL_INTERVAL:
                serial_manager.send("status")
                last_status_poll = now

            time.sleep(LOOP_SLEEP)

    except KeyboardInterrupt as e:
        print(f"\n[BACKEND] salida: {e}")
    except Exception as e:
        print(f"\n[BACKEND ERROR] {e}")
    finally:
        if ws_server:
            ws_server.stop()
        if serial_manager:
            serial_manager.disconnect()


if __name__ == "__main__":
    main()
