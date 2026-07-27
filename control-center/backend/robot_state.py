"""Estado thread-safe que comparten serial, joystick, percepcion y WebSocket."""

from __future__ import annotations

import threading
import time
from collections import deque
from copy import deepcopy
from typing import Any

from config import REALSENSE_MODEL, REALSENSE_SERIAL, SERVO_SPECS


class RobotState:
    def __init__(self):
        self._lock = threading.RLock()
        self._revision = 0
        self.state = {
            "protocol_version": 2,
            "connected": False,
            "port": None,
            "runtime_mode": "hardware",
            "mode": "manual",
            "joystick_connected": False,
            "servos": {
                spec.name: {
                    "id": spec.servo_id,
                    "current": spec.home,
                    "target": spec.home,
                    "min": spec.min_angle,
                    "max": spec.max_angle,
                    "pca_channel": spec.pca_channel,
                    "measured": False,
                }
                for spec in SERVO_SPECS
            },
            "joystick": {
                "axis0": 0.0,
                "axis1": 0.0,
                "hat": [0, 0],
                "buttons": [0] * 8,
            },
            "perception": {
                "enabled": False,
                "source": "off",
                "status": "inactive",
                "model": REALSENSE_MODEL,
                "serial": REALSENSE_SERIAL,
                "coordinate_frame": "robot_base",
                "calibrated": False,
                "frame_id": 0,
                "fps": 0.0,
                "point_count": 0,
                "closest_distance_m": None,
                "points": [],
                "obstacles": [],
                "error": None,
            },
            "health": {
                "started_at": time.time(),
                "last_command_at": None,
                "last_error": None,
            },
            "logs": deque(maxlen=200),
        }

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    def _touch(self) -> None:
        self._revision += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            snap = deepcopy(self.state)
            snap["logs"] = list(snap["logs"])
            snap["revision"] = self._revision
            snap["health"]["uptime_s"] = round(
                time.time() - snap["health"]["started_at"], 1
            )
            return snap

    def get_mode(self) -> str:
        with self._lock:
            return self.state["mode"]

    def servo_currents(self) -> dict[int, int]:
        with self._lock:
            return {
                servo["id"]: servo["current"]
                for servo in self.state["servos"].values()
            }

    def set_runtime_mode(self, runtime_mode: str) -> None:
        with self._lock:
            self.state["runtime_mode"] = runtime_mode
            self._touch()

    def set_connected(self, connected: bool, port: str | None = None) -> None:
        with self._lock:
            self.state["connected"] = connected
            self.state["port"] = port
            self._touch()

    def set_mode(self, mode: str) -> None:
        with self._lock:
            if self.state["mode"] != mode:
                self.state["mode"] = mode
                self._touch()

    def set_joystick_connected(self, connected: bool) -> None:
        with self._lock:
            if self.state["joystick_connected"] != connected:
                self.state["joystick_connected"] = connected
                self._touch()

    def set_joystick_state(
        self,
        axis0: float,
        axis1: float,
        hat: tuple[int, int],
        buttons: list[int],
    ) -> None:
        with self._lock:
            joystick = self.state["joystick"]
            next_value = {
                "axis0": round(axis0, 3),
                "axis1": round(axis1, 3),
                "hat": [hat[0], hat[1]],
                "buttons": buttons[:8],
            }
            if joystick != next_value:
                self.state["joystick"] = next_value
                self._touch()

    def update_servo_target(self, servo_id: int, target: int) -> None:
        with self._lock:
            servo = self._servo_by_id(servo_id)
            if servo and servo["target"] != target:
                servo["target"] = target
                self.state["health"]["last_command_at"] = time.time()
                self._touch()

    def update_servo_current(self, servo_id: int, current: int) -> None:
        with self._lock:
            servo = self._servo_by_id(servo_id)
            if servo and servo["current"] != current:
                servo["current"] = current
                self._touch()

    def update_from_status_line(
        self,
        servo_name: str,
        pca_channel: int,
        current: int,
        target: int,
        min_angle: int,
        max_angle: int,
    ) -> None:
        with self._lock:
            if servo_name not in self.state["servos"]:
                return
            servo = self.state["servos"][servo_name]
            next_values = {
                "pca_channel": pca_channel,
                "current": current,
                "target": target,
                "min": min_angle,
                "max": max_angle,
            }
            changed = any(servo[key] != value for key, value in next_values.items())
            servo.update(next_values)
            if changed:
                self._touch()

    def update_perception(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self.state["perception"].update(payload)
            self._touch()

    def set_error(self, text: str | None) -> None:
        with self._lock:
            self.state["health"]["last_error"] = text
            self._touch()

    def add_log(self, text: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        with self._lock:
            self.state["logs"].append(f"{timestamp}  {text}")
            self._touch()

    def _servo_by_id(self, servo_id: int) -> dict[str, Any] | None:
        for servo in self.state["servos"].values():
            if servo["id"] == servo_id:
                return servo
        return None
