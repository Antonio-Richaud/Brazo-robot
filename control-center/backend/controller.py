"""Coordinador de comandos, modos y sincronizacion con el firmware."""

from __future__ import annotations

import threading
import time
from typing import Any

from config import HOME, LIMITS, SEND_INTERVAL, SERVO_NAMES, STATUS_POLL_INTERVAL


SIMULATION_SEQUENCES = {
    "saludo": [
        (2.6, 0.45, {1: 90, 2: 60, 3: 90, 4: 90, 5: 100, 6: 40}),
        (2.8, 0.15, HOME),
    ],
    "rutina": [
        (2.4, 0.22, {1: 123, 2: 132, 3: 102, 4: 95, 5: 77, 6: 81}),
        (0.95, 0.16, {1: 123, 2: 132, 3: 102, 4: 95, 5: 77, 6: 20}),
        (2.3, 0.22, {1: 123, 2: 57, 3: 165, 4: 95, 5: 77, 6: 20}),
        (1.9, 0.22, {1: 51, 2: 63, 3: 165, 4: 95, 5: 77, 6: 20}),
        (2.4, 0.22, {1: 50, 2: 139, 3: 86, 4: 95, 5: 77, 6: 20}),
        (1.0, 0.18, {1: 50, 2: 139, 3: 86, 4: 95, 5: 77, 6: 92}),
        (2.8, 0.18, HOME),
    ],
}


class RobotController:
    def __init__(self, state, serial_manager=None, simulation: bool = False):
        self.state = state
        self.serial_manager = serial_manager
        self.joystick_manager = None
        self.simulation = simulation
        self._lock = threading.RLock()
        self.targets = {servo_id: float(value) for servo_id, value in HOME.items()}
        self.last_sent = {servo_id: None for servo_id in HOME}
        self.manual_enabled = True
        self._last_send = 0.0
        self._last_status_poll = 0.0
        self._simulation_sequence: dict[str, Any] | None = None

    def attach_joystick(self, joystick_manager) -> None:
        with self._lock:
            self.joystick_manager = joystick_manager
            joystick_manager.targets = self.targets
            joystick_manager.last_sent = self.last_sent
            joystick_manager.set_manual_enabled(self.manual_enabled)

    def handle_protocol_event(self, event: str) -> None:
        """Mantiene alineados firmware, UI y joystick al terminar secuencias."""
        with self._lock:
            if event == "saludo_started":
                self._set_mode("saludo", manual=False)
            elif event == "rutina_started":
                self._set_mode("rutina", manual=False)
            elif event in {"saludo_finished", "rutina_finished", "choreo_stopped", "home"}:
                self._reset_home(sync=True)
                self._set_mode("manual", manual=True)

    def handle_command(self, data: dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False
        action = data.get("action")
        if not isinstance(action, str):
            return False

        with self._lock:
            if action == "home":
                self._send("home")
                self._reset_home(sync=True)
                self._set_mode("manual", manual=True)
                return True

            if action in {"saludo", "rutina"}:
                if self.state.get_mode() != "manual":
                    return False
                self._send(action)
                self._set_mode(action, manual=False)
                if self.simulation:
                    self._start_simulation_sequence(action)
                return True

            if action == "stop":
                self._send("stop")
                self._reset_home(sync=True)
                self._set_mode("manual", manual=True)
                return True

            if action == "set_servo":
                if self.state.get_mode() != "manual":
                    return False
                try:
                    servo_id = int(data["servo_id"])
                    angle = float(data["angle"])
                except (KeyError, TypeError, ValueError):
                    return False
                if servo_id not in self.targets:
                    return False
                low, high = LIMITS[servo_id]
                angle = max(low, min(high, angle))
                self.targets[servo_id] = angle
                # Solo se reenvia el servo que cambio, no los seis.
                self.last_sent[servo_id] = None
                self.state.update_servo_target(servo_id, round(angle))
                return True

        return False

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            if self.manual_enabled and now - self._last_send >= SEND_INTERVAL:
                changed = False
                for servo_id in sorted(self.targets):
                    angle = round(self.targets[servo_id])
                    if self.last_sent[servo_id] == angle:
                        continue
                    if self._send(f"s {servo_id} {angle}"):
                        self.last_sent[servo_id] = angle
                    self.state.update_servo_target(servo_id, angle)
                    changed = True
                if changed:
                    self._last_send = now

            if self.simulation:
                self._tick_simulation(now)
            elif (
                self.serial_manager
                and self.serial_manager.connected
                and now - self._last_status_poll >= STATUS_POLL_INTERVAL
                and now - self._last_send >= 0.20
            ):
                self.serial_manager.send("status")
                self._last_status_poll = now

    def _send(self, command: str) -> bool:
        if self.simulation:
            if command not in {"status"} and not command.startswith("s "):
                self.state.add_log(f"[SIM] {command}")
            return True
        return bool(self.serial_manager and self.serial_manager.send(command))

    def _set_mode(self, mode: str, manual: bool) -> None:
        self.manual_enabled = manual
        self.state.set_mode(mode)
        if self.joystick_manager:
            self.joystick_manager.set_manual_enabled(manual)

    def _reset_home(self, sync: bool) -> None:
        for servo_id, angle in HOME.items():
            self.targets[servo_id] = float(angle)
            self.state.update_servo_target(servo_id, angle)
            if sync:
                self.last_sent[servo_id] = None

    def _start_simulation_sequence(self, name: str) -> None:
        currents = self.state.servo_currents()
        self._simulation_sequence = {
            "name": name,
            "steps": SIMULATION_SEQUENCES[name],
            "index": 0,
            "started": time.monotonic(),
            "from": currents,
        }

    @staticmethod
    def _smoother_step(value: float) -> float:
        value = max(0.0, min(1.0, value))
        return value**3 * (value * (value * 6 - 15) + 10)

    def _tick_simulation(self, now: float) -> None:
        if self._simulation_sequence:
            sequence = self._simulation_sequence
            duration, hold, pose = sequence["steps"][sequence["index"]]
            elapsed = now - sequence["started"]
            progress = min(1.0, elapsed / max(0.001, duration))
            eased = self._smoother_step(progress)
            for servo_id, name in SERVO_NAMES.items():
                start = sequence["from"][servo_id]
                target = pose[servo_id]
                current = round(start + (target - start) * eased)
                self.state.update_servo_current(servo_id, current)
                self.state.update_servo_target(servo_id, target)

            if elapsed >= duration + hold:
                sequence["index"] += 1
                if sequence["index"] >= len(sequence["steps"]):
                    name = sequence["name"]
                    self._simulation_sequence = None
                    self.handle_protocol_event(f"{name}_finished")
                else:
                    sequence["started"] = now
                    sequence["from"] = {
                        servo_id: pose[servo_id] for servo_id in SERVO_NAMES
                    }
            return

        currents = self.state.servo_currents()
        for servo_id in SERVO_NAMES:
            current = currents[servo_id]
            target = round(self.targets[servo_id])
            difference = target - current
            if difference:
                step = max(-3, min(3, difference))
                self.state.update_servo_current(servo_id, current + step)
