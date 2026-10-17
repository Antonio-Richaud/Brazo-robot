"""Control directo del PCA9685 desde Raspberry Pi 4, sin ESP32.

Replica el integrador de velocidad/aceleracion y las coreografias del firmware.
Los angulos son estimaciones: MG995/SG90 no tienen realimentacion de posicion.
El bus I2C y la libreria Adafruit se importan solo al conectar hardware.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass
from typing import Callable

from config import HOME, SERVO_SPECS, ServoSpec
from controller import SIMULATION_SEQUENCES

PWM_HZ = 50
PWM_PERIOD_US = 1_000_000 / PWM_HZ
MOTION_INTERVAL_S = 0.020
MAX_DT_S = 0.050
MAX_SPEED_DEG_S = 85.0
MAX_ACCEL_DEG_S2 = 260.0
POSITION_EPS = 0.20
VELOCITY_EPS = 1.0


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def smootherstep(progress: float) -> float:
    t = clamp(progress, 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


@dataclass
class Axis:
    spec: ServoSpec
    home: float
    minimum: float
    maximum: float
    current: float
    target: float
    velocity: float = 0.0

    @classmethod
    def from_spec(cls, spec: ServoSpec) -> "Axis":
        return cls(
            spec=spec,
            home=float(spec.home),
            minimum=float(spec.min_angle),
            maximum=float(spec.max_angle),
            current=float(spec.home),
            target=float(spec.home),
        )


class RaspberryPiMotionDriver:
    """Transporte local compatible con send/tick del RobotController.

    connect() NO habilita PWM. Es obligatorio llamar arm() de forma explicita
    una vez colocado FISICAMENTE el robot en Home y despejada su trayectoria.
    disarm() libera PWM, pero NO corta la alimentacion externa de los servos.
    """

    requires_arm = True

    def __init__(
        self,
        state,
        address: int = 0x40,
        pca_factory: Callable[[], object] | None = None,
        event_handler: Callable[[str], None] | None = None,
    ):
        self.state = state
        self.address = address
        self.event_handler = event_handler
        self._pca_factory = pca_factory or self._make_pca
        self._pca = None
        self._lock = threading.RLock()
        self.armed = False
        self.axes = {spec.servo_id: Axis.from_spec(spec) for spec in SERVO_SPECS}
        self._last_motion_at: float | None = None
        self._sequence: dict | None = None

    @staticmethod
    def _make_pca():
        try:
            import board
            from adafruit_pca9685 import PCA9685
        except ImportError as exc:
            raise RuntimeError(
                "Falta el controlador PCA9685. Instala requirements-raspberry-pi.txt "
                "en una Raspberry Pi con I2C habilitado."
            ) from exc
        # board.I2C() usa GPIO2/SDA y GPIO3/SCL en la Raspberry Pi 4.
        return PCA9685(board.I2C())

    @property
    def connected(self) -> bool:
        return self._pca is not None

    def connect(self) -> str:
        with self._lock:
            if self.connected:
                return self._label()
            pca = self._pca_factory()
            try:
                pca.frequency = PWM_HZ
                # Suelta los seis canales antes de aceptar cualquier movimiento.
                for axis in self.axes.values():
                    pca.channels[axis.spec.pca_channel].duty_cycle = 0
            except Exception:
                try:
                    pca.deinit()
                except Exception:
                    pass
                raise

            self._pca = pca
            self.armed = False
            self._sequence = None
            self.state.set_connected(True, self._label())
            self.state.set_armed(False)
            self.state.set_error(None)
            self._publish_all()
            self.state.add_log("[PI4] PCA9685 detectado; salidas PWM desarmadas")
            return self._label()

    def _label(self) -> str:
        return f"I2C-1 / 0x{self.address:02X}"

    def arm(self) -> bool:
        with self._lock:
            if not self.connected:
                return False
            if self.armed:
                return True

            # No hay encoder: se supone que el operador coloco el brazo
            # fisicamente en Home ANTES de habilitarlo.
            for axis in self.axes.values():
                axis.current = axis.home
                axis.target = axis.home
                axis.velocity = 0.0
            self._sequence = None
            self._last_motion_at = time.monotonic()
            try:
                for axis in self.axes.values():
                    self._write_angle(axis, axis.current)
            except Exception as exc:
                self._fault(exc)
                return False
            self.armed = True
            self.state.set_armed(True)
            self._publish_all()
            self.state.add_log("[PI4] PWM habilitado en Home (posicion estimada)")
            return True

    def disarm(self) -> bool:
        with self._lock:
            self._sequence = None
            self._last_motion_at = None
            self.armed = False
            try:
                self._disable_pwm()
            except Exception as exc:
                self._fault(exc)
                return False
            self.state.set_armed(False)
            self.state.add_log(
                "[PI4] PWM deshabilitado; esto NO corta la potencia de los servos"
            )
            return True

    def disconnect(self) -> None:
        with self._lock:
            self.armed = False
            self._sequence = None
            self._last_motion_at = None
            pca = self._pca
            if pca is not None:
                try:
                    self._disable_pwm()
                except Exception:
                    pass
                try:
                    pca.deinit()
                except Exception:
                    pass
            self._pca = None
            self.state.set_armed(False)
            self.state.set_connected(False, None)

    def _disable_pwm(self) -> None:
        if self._pca is not None:
            for axis in self.axes.values():
                self._pca.channels[axis.spec.pca_channel].duty_cycle = 0

    def _fault(self, exc: Exception) -> None:
        self.state.add_log(f"[PI4 ERROR] Fallo I2C/PWM: {exc}")
        self.state.set_error(str(exc))
        self.disconnect()

    def _write_angle(self, axis: Axis, angle: float) -> None:
        """Misma transformacion angular 500-2500 us que el firmware original.

        Los pulsos son parametros provisionales, no calibracion certificada.
        """
        angle = clamp(angle, axis.minimum, axis.maximum)
        pulse_us = axis.spec.min_us + (angle / 180.0) * (
            axis.spec.max_us - axis.spec.min_us
        )
        duty = round(pulse_us / PWM_PERIOD_US * 65535)
        self._pca.channels[axis.spec.pca_channel].duty_cycle = int(
            clamp(duty, 0, 65535)
        )
        axis.current = angle
        self.state.update_servo_current(axis.spec.servo_id, round(angle))

    def _publish_axis(self, axis: Axis) -> None:
        self.state.update_from_status_line(
            axis.spec.name,
            axis.spec.pca_channel,
            round(axis.current),
            round(axis.target),
            round(axis.minimum),
            round(axis.maximum),
        )

    def _publish_all(self) -> None:
        for axis in self.axes.values():
            self._publish_axis(axis)

    def _set_target(self, axis: Axis, target: float) -> None:
        axis.target = clamp(target, axis.minimum, axis.maximum)
        axis.velocity = 0.0
        self._publish_axis(axis)

    def _home(self) -> None:
        self._sequence = None
        self._last_motion_at = time.monotonic()
        for axis in self.axes.values():
            self._set_target(axis, axis.home)

    def send(self, command: str) -> bool:
        with self._lock:
            if not self.connected:
                return False
            parts = command.strip().split()
            if not parts:
                return False
            op = parts[0].lower()
            if op == "status" and len(parts) == 1:
                self._publish_all()
                return True
            if not self.armed:
                return False
            if self._sequence and op not in {"stop", "status"}:
                return False

            if op in {"home", "stop"} and len(parts) == 1:
                self._home()
                if op == "stop" and self.event_handler:
                    self.event_handler("choreo_stopped")
                elif op == "home" and self.event_handler:
                    self.event_handler("home")
                return True

            if op in SIMULATION_SEQUENCES and len(parts) == 1:
                self._sequence = {
                    "name": op,
                    "steps": SIMULATION_SEQUENCES[op],
                    "index": 0,
                    "started": time.monotonic(),
                    "from": {servo_id: axis.current for servo_id, axis in self.axes.items()},
                }
                for axis in self.axes.values():
                    axis.velocity = 0.0
                self.state.add_log(f"[PI4] {op} iniciada")
                if self.event_handler:
                    self.event_handler(f"{op}_started")
                return True

            if op not in {"s", "d", "homev", "range"}:
                return False
            try:
                servo_id = int(parts[1])
                axis = self.axes[servo_id]
                expected = 4 if op == "range" else 3
                if len(parts) != expected:
                    return False
                values = [float(value) for value in parts[2:]]
                if not all(math.isfinite(value) for value in values):
                    return False
            except (IndexError, ValueError, KeyError, TypeError):
                return False

            if op == "s":
                self._set_target(axis, values[0])
            elif op == "d":
                self._set_target(axis, axis.target + values[0])
            elif op == "homev":
                axis.home = clamp(values[0], axis.minimum, axis.maximum)
            elif op == "range":
                low, high = values
                if not (0 <= low < high <= 180):
                    return False
                axis.minimum, axis.maximum = low, high
                axis.home = clamp(axis.home, low, high)
                axis.target = clamp(axis.target, low, high)
                axis.current = clamp(axis.current, low, high)
                axis.velocity = 0.0
                try:
                    self._write_angle(axis, axis.current)
                except Exception as exc:
                    self._fault(exc)
                    return False
            self._publish_axis(axis)
            return True

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            if not self.connected or not self.armed:
                return
            try:
                if self._sequence:
                    self._tick_sequence(now)
                else:
                    self._tick_manual(now)
            except Exception as exc:
                self._fault(exc)

    def _tick_sequence(self, now: float) -> None:
        sequence = self._sequence
        duration, hold, pose = sequence["steps"][sequence["index"]]
        elapsed = max(0.0, now - sequence["started"])
        eased = smootherstep(elapsed / max(0.001, duration))

        for servo_id, axis in self.axes.items():
            target = clamp(float(pose[servo_id]), axis.minimum, axis.maximum)
            start = sequence["from"][servo_id]
            current = start + (target - start) * eased
            self._write_angle(axis, current)
            # Igual que firmware: durante coreografia el objetivo publicado
            # representa la posicion interpolada.
            axis.target = current
            self._publish_axis(axis)

        if elapsed < duration + hold:
            return

        sequence["index"] += 1
        if sequence["index"] >= len(sequence["steps"]):
            name = sequence["name"]
            self._sequence = None
            self._last_motion_at = now
            for axis in self.axes.values():
                self._set_target(axis, axis.home)
            self.state.add_log(f"[PI4] {name} terminada")
            if self.event_handler:
                self.event_handler(f"{name}_finished")
        else:
            sequence["started"] = now
            sequence["from"] = {
                servo_id: axis.current for servo_id, axis in self.axes.items()
            }

    def _tick_manual(self, now: float) -> None:
        if self._last_motion_at is None:
            self._last_motion_at = now
            return
        elapsed = now - self._last_motion_at
        if elapsed < MOTION_INTERVAL_S:
            return
        dt = clamp(elapsed, 0.0, MAX_DT_S)
        self._last_motion_at = now

        for axis in self.axes.values():
            error = axis.target - axis.current
            if abs(error) < POSITION_EPS and abs(axis.velocity) < VELOCITY_EPS:
                # Evita I2C redundante cuando la articulacion esta quieta.
                if axis.current != axis.target:
                    self._write_angle(axis, axis.target)
                axis.velocity = 0.0
                continue

            desired = clamp(error * 4.2, -MAX_SPEED_DEG_S, MAX_SPEED_DEG_S)
            delta_v = clamp(
                desired - axis.velocity,
                -MAX_ACCEL_DEG_S2 * dt,
                MAX_ACCEL_DEG_S2 * dt,
            )
            axis.velocity += delta_v
            next_pos = axis.current + axis.velocity * dt

            if (error > 0 and next_pos > axis.target) or (
                error < 0 and next_pos < axis.target
            ):
                next_pos = axis.target
                axis.velocity = 0.0

            self._write_angle(axis, next_pos)
            self._publish_axis(axis)
