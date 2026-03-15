import threading
from collections import deque
from copy import deepcopy

from config import HOME, SERVO_NAMES


class RobotState:
    def __init__(self):
        self._lock = threading.Lock()
        self.state = {
            "connected": False,
            "port": None,
            "mode": "manual",
            "joystick_connected": False,
            "servos": {
                SERVO_NAMES[i]: {
                    "id": i,
                    "current": HOME[i],
                    "target": HOME[i],
                    "min": None,
                    "max": None,
                    "pca_channel": None,
                }
                for i in range(1, 7)
            },
            "joystick": {
                "axis0": 0.0,
                "axis1": 0.0,
                "hat": [0, 0],
                "buttons": [0] * 8,
            },
            "logs": deque(maxlen=300),
        }

    def snapshot(self):
        with self._lock:
            snap = deepcopy(self.state)
            snap["logs"] = list(snap["logs"])
            return snap

    def set_connected(self, connected: bool, port: str | None = None):
        with self._lock:
            self.state["connected"] = connected
            self.state["port"] = port

    def set_mode(self, mode: str):
        with self._lock:
            self.state["mode"] = mode

    def set_joystick_connected(self, connected: bool):
        with self._lock:
            self.state["joystick_connected"] = connected

    def set_joystick_state(self, axis0: float, axis1: float, hat: tuple[int, int], buttons: list[int]):
        with self._lock:
            self.state["joystick"]["axis0"] = axis0
            self.state["joystick"]["axis1"] = axis1
            self.state["joystick"]["hat"] = [hat[0], hat[1]]
            self.state["joystick"]["buttons"] = buttons[:]

    def update_servo_target(self, servo_id: int, target: int):
        name = SERVO_NAMES[servo_id]
        with self._lock:
            self.state["servos"][name]["target"] = target

    def update_from_status_line(self, servo_name: str, pca_channel: int, current: int, target: int, min_angle: int, max_angle: int):
        with self._lock:
            if servo_name not in self.state["servos"]:
                return
            self.state["servos"][servo_name]["pca_channel"] = pca_channel
            self.state["servos"][servo_name]["current"] = current
            self.state["servos"][servo_name]["target"] = target
            self.state["servos"][servo_name]["min"] = min_angle
            self.state["servos"][servo_name]["max"] = max_angle

    def add_log(self, text: str):
        with self._lock:
            self.state["logs"].append(text)
