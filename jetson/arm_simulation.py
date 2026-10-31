#!/usr/bin/env python3
"""Simulacion AISLADA del brazo de seis articulaciones para Jetson Nano 2GB.

Compatible con Python 3.6 sin dependencias externas. NO importa ni utiliza
I2C, GPIO, PWM, puertos seriales, red, ni el controlador PCA9685.

El armado de este simulador JAMAS habilita motores fisicos.
Los angulos actuales aqui son estimaciones matematicas, NO lecturas de servos.
Los parametros se copian de control-center/backend/config.py; al modificarlos,
revisar y probar ambos lados. Los limites todavia NO estan calibrados
fisicamente para un montaje Jetson.
"""

import argparse
import json
import math
import time
from collections import namedtuple


JointSpec = namedtuple(
    "JointSpec",
    "servo_id name pca_channel home min_angle max_angle rate_deg_s",
)

# Copia explicita del contrato de control-center/backend/config.py.
JOINTS = (
    JointSpec(1, "base", 0, 90, 10, 170, 70.0),
    JointSpec(2, "hombro", 1, 50, 15, 165, 55.0),
    JointSpec(3, "codo", 2, 165, 15, 165, 70.0),
    JointSpec(4, "muneca1", 3, 10, 10, 170, 90.0),
    JointSpec(5, "muneca2", 4, 170, 10, 170, 90.0),
    JointSpec(6, "garra", 5, 40, 20, 140, 90.0),
)

JOINT_BY_ID = {spec.servo_id: spec for spec in JOINTS}

DISARMED = "DISARMED"
SIM_ARMED = "SIM_ARMED"
FAULT = "FAULT"


def _positive_finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("{} debe ser numerico".format(name))
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("{} debe ser finito y positivo".format(name))
    return number


class ArmSimulation(object):
    """Modelo sin salida fisica: solo cambia datos mantenidos en RAM.

    El temporizador watchdog funciona cuando se llama tick() o heartbeat()
    o se intenta una orden. No es un watchdog de hardware ni un paro real.
    """

    def __init__(self, clock=None, watchdog_s=1.0, max_step_s=0.1):
        self._clock = clock or time.monotonic
        if not callable(self._clock):
            raise ValueError("El reloj debe ser una funcion")
        self.watchdog_s = _positive_finite(watchdog_s, "watchdog_s")
        self.max_step_s = _positive_finite(max_step_s, "max_step_s")
        self.state = DISARMED
        self.fault_reason = None
        self.positions = {
            spec.servo_id: float(spec.home) for spec in JOINTS
        }
        self.targets = dict(self.positions)
        self._last_tick = self._now()
        self._last_keepalive = None

    def _now(self):
        value = self._clock()
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Tiempo del reloj invalido")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("Tiempo del reloj no finito")
        return value

    def _enter_fault(self, reason):
        self.state = FAULT
        self.fault_reason = reason
        # Detener el movimiento SIMULADO en la posicion actual, NO enviar Home.
        self.targets = dict(self.positions)
        self._last_keepalive = None

    def _require_live_simulation(self, now):
        if self.state != SIM_ARMED:
            raise RuntimeError("Simulacion no armada; estado: {}".format(self.state))
        if now < self._last_tick or now < self._last_keepalive:
            self._enter_fault("Reloj monotonicamente inconsistente")
            raise RuntimeError(self.fault_reason)
        if now - self._last_keepalive > self.watchdog_s:
            self._enter_fault("Watchdog de simulacion: sin heartbeat")
            raise RuntimeError(self.fault_reason)

    def arm_simulation(self):
        """Armado SOLO en memoria; no existe accion de armar PCA9685."""
        if self.state != DISARMED:
            raise RuntimeError("Solo se arma simulacion desde DISARMED")
        now = self._now()
        self.state = SIM_ARMED
        self.fault_reason = None
        self._last_tick = now
        self._last_keepalive = now

    def heartbeat(self):
        """Mantiene vivo exclusivamente el modelo matematico."""
        now = self._now()
        self._require_live_simulation(now)
        self._last_keepalive = now

    def set_target(self, servo_id, angle_deg):
        """Valida un objetivo simulado; nunca produce pulsos fisicos."""
        if type(servo_id) is not int or servo_id not in JOINT_BY_ID:
            raise ValueError("Servo invalido: solo IDs 1..6")
        if isinstance(angle_deg, bool) or not isinstance(angle_deg, (int, float)):
            raise ValueError("Angulo debe ser numerico")
        angle = float(angle_deg)
        if not math.isfinite(angle):
            raise ValueError("Angulo debe ser finito")
        spec = JOINT_BY_ID[servo_id]
        if not spec.min_angle <= angle <= spec.max_angle:
            raise ValueError(
                "{} fuera de limites [{}, {}] grados".format(
                    spec.name, spec.min_angle, spec.max_angle
                )
            )
        now = self._now()
        self._require_live_simulation(now)
        self.targets[servo_id] = angle
        self._last_keepalive = now

    def tick(self):
        """Avanza posiciones simuladas con limite de velocidad y tiempo.

        No acelera sobre el tiempo perdido tras una pausa; max_step_s limita
        el avance de cada invocacion. Despues de un fallo, no hay movimiento.
        """
        if self.state != SIM_ARMED:
            return self.snapshot()
        now = self._now()
        try:
            self._require_live_simulation(now)
        except RuntimeError:
            return self.snapshot()
        elapsed = min(now - self._last_tick, self.max_step_s)
        for spec in JOINTS:
            current = self.positions[spec.servo_id]
            target = self.targets[spec.servo_id]
            maximum = spec.rate_deg_s * elapsed
            change = max(-maximum, min(maximum, target - current))
            self.positions[spec.servo_id] = current + change
        self._last_tick = now
        return self.snapshot()

    def disarm_simulation(self):
        """Congela las posiciones simuladas. No hay orden fisica de corte."""
        if self.state == FAULT:
            raise RuntimeError("FAULT requiere reset_fault explicito")
        self.state = DISARMED
        self.targets = dict(self.positions)
        self._last_keepalive = None
        self._last_tick = self._now()

    def reset_fault(self):
        """Reconoce fallo y pasa a DISARMED; no vuelve a armar solo."""
        if self.state != FAULT:
            raise RuntimeError("Solo se permite reset_fault desde FAULT")
        self.state = DISARMED
        self.fault_reason = None
        self.targets = dict(self.positions)
        self._last_keepalive = None
        self._last_tick = self._now()

    def snapshot(self):
        """Devuelve datos nuevos en cada llamada (no expone estado mutable)."""
        servos = {}
        for spec in JOINTS:
            servos[spec.name] = {
                "id": spec.servo_id,
                "pca_channel": spec.pca_channel,
                "current": round(self.positions[spec.servo_id], 3),
                "target": round(self.targets[spec.servo_id], 3),
                "min": spec.min_angle,
                "max": spec.max_angle,
                "measured": False,
            }
        return {
            "mode": "simulation_only",
            "hardware_enabled": False,
            "state": self.state,
            "fault_reason": self.fault_reason,
            "watchdog_s": self.watchdog_s,
            "servos": servos,
        }


class _DemoClock(object):
    """Reloj determinista para demostrar resultados sin esperas ni I/O."""

    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def run_demo():
    clock = _DemoClock()
    sim = ArmSimulation(clock=clock)
    print("=== SIMULACION: 0 ACCESO A HARDWARE ===")
    print("INICIAL", json.dumps(sim.snapshot(), sort_keys=True))
    sim.arm_simulation()
    sim.set_target(1, 125)
    for _ in range(5):
        clock.advance(0.1)
        sim.heartbeat()
        sim.tick()
        print("T={:.1f}s base={:.1f} deg".format(
            clock.value, sim.snapshot()["servos"]["base"]["current"]
        ))
    sim.disarm_simulation()
    print("FINAL", json.dumps(sim.snapshot(), sort_keys=True))
    print("SIMULACION TERMINADA: sin motores, sin I2C y sin GPIO")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sandbox matematico del brazo")
    parser.add_argument(
        "--demo", action="store_true",
        help="demostracion determinista SIN acceso a hardware"
    )
    args = parser.parse_args(argv)
    if not args.demo:
        parser.error("Para ejecutar: --demo (exclusivamente simulacion)")
    run_demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
