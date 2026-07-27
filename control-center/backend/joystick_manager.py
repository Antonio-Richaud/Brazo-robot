"""Lectura del joystick desacoplada del transporte serial."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from config import (
    BASE_RATE,
    CALIBRATION_SECONDS,
    CODO_RATE,
    DEADZONE,
    GARRA_RATE,
    HOMBRO_RATE,
    HOME,
    LIMITS,
    MAX_CONTROL_DT,
    MUNECA1_RATE,
    MUNECA2_RATE,
)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_axis(raw: float, center: float, deadzone: float = DEADZONE) -> float:
    if raw >= center:
        value = (raw - center) / max(0.001, 1.0 - center)
    else:
        value = (raw - center) / max(0.001, center + 1.0)

    value = clamp(value, -1.0, 1.0)
    if abs(value) < deadzone:
        return 0.0
    if value > 0:
        value = (value - deadzone) / (1.0 - deadzone)
    else:
        value = (value + deadzone) / (1.0 - deadzone)
    return clamp(value, -1.0, 1.0)


class JoystickManager:
    def __init__(
        self,
        state,
        action_handler: Callable[[dict[str, Any]], None] | None = None,
        device_index: int = 0,
    ):
        self.state = state
        self.action_handler = action_handler

        try:
            import pygame
        except ImportError as exc:
            raise RuntimeError("Falta pygame; instala requirements.txt para usar el joystick.") from exc
        self.pygame = pygame
        pygame.init()
        pygame.joystick.init()
        count = pygame.joystick.get_count()
        if count <= device_index:
            raise RuntimeError("No se detecto ningun joystick compatible.")

        self.js = pygame.joystick.Joystick(device_index)
        self.js.init()
        self.state.set_joystick_connected(True)
        self.state.add_log(f"[JOYSTICK] {self.js.get_name()}")

        self.axis_centers = self._calibrate()
        self.targets = {servo_id: float(angle) for servo_id, angle in HOME.items()}
        self.last_sent = {servo_id: None for servo_id in HOME}
        self.last_buttons: dict[str, int] = {}
        self.manual_enabled = True

    def _calibrate(self) -> list[float]:
        self.state.add_log(
            f"[JOYSTICK] calibrando durante {CALIBRATION_SECONDS:.1f} s; dejalo quieto"
        )
        axis_count = self.js.get_numaxes()
        axis_sums = [0.0] * axis_count
        samples = 0
        started = time.monotonic()
        while time.monotonic() - started < CALIBRATION_SECONDS:
            self.pygame.event.pump()
            for index in range(axis_count):
                axis_sums[index] += self.js.get_axis(index)
            samples += 1
            time.sleep(0.01)
        return [total / max(1, samples) for total in axis_sums]

    def close(self) -> None:
        self.state.set_joystick_connected(False)
        try:
            self.js.quit()
        finally:
            self.pygame.joystick.quit()
            self.pygame.quit()

    def set_manual_enabled(self, enabled: bool) -> None:
        self.manual_enabled = enabled

    def reset_home(self) -> None:
        self.targets = {servo_id: float(angle) for servo_id, angle in HOME.items()}
        self.force_sync_targets()

    def set_target(self, servo_id: int, angle: float) -> None:
        low, high = LIMITS[servo_id]
        self.targets[servo_id] = clamp(angle, low, high)
        self.last_sent[servo_id] = None

    def force_sync_targets(self) -> None:
        for servo_id in self.targets:
            self.last_sent[servo_id] = None

    def _emit(self, action: str) -> None:
        if self.action_handler:
            self.action_handler({"action": action, "source": "joystick"})

    def _button(self, index: int) -> int:
        return self.js.get_button(index) if self.js.get_numbuttons() > index else 0

    def tick(self, dt: float) -> None:
        self.pygame.event.pump()
        dt = clamp(dt, 0.0, MAX_CONTROL_DT)

        ax0 = (
            normalize_axis(self.js.get_axis(0), self.axis_centers[0])
            if self.js.get_numaxes() > 0
            else 0.0
        )
        ax1 = (
            normalize_axis(self.js.get_axis(1), self.axis_centers[1])
            if self.js.get_numaxes() > 1
            else 0.0
        )
        hat_x, hat_y = self.js.get_hat(0) if self.js.get_numhats() else (0, 0)
        buttons = [self._button(index) for index in range(8)]

        self.state.set_joystick_state(ax0, ax1, (hat_x, hat_y), buttons)

        actions = ((4, "home"), (5, "saludo"), (6, "stop"), (7, "rutina"))
        for index, action in actions:
            key = f"b{index}"
            if buttons[index] and not self.last_buttons.get(key, 0):
                self._emit(action)
            self.last_buttons[key] = buttons[index]

        if not self.manual_enabled:
            return

        self.targets[1] += (-ax0) * BASE_RATE * dt
        self.targets[2] += (-ax1) * HOMBRO_RATE * dt

        if buttons[2] and not buttons[3]:
            self.targets[3] -= CODO_RATE * dt
        elif buttons[3] and not buttons[2]:
            self.targets[3] += CODO_RATE * dt

        self.targets[4] += hat_x * MUNECA1_RATE * dt
        self.targets[5] += (-hat_y) * MUNECA2_RATE * dt

        if buttons[0] and not buttons[1]:
            self.targets[6] -= GARRA_RATE * dt
        elif buttons[1] and not buttons[0]:
            self.targets[6] += GARRA_RATE * dt

        for servo_id, target in self.targets.items():
            low, high = LIMITS[servo_id]
            self.targets[servo_id] = clamp(target, low, high)
