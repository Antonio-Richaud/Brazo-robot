#!/usr/bin/env python3
"""Emite JSON Lines de una demostracion MATEMATICA del brazo en Jetson.

Compatible con Python 3.6 y solo biblioteca estandar. No abre sockets, no lee
stdin, no usa I2C/GPIO/serial/PWM ni energiza servos.

El estado SIM_ARMED pertenece EXCLUSIVAMENTE al modelo matematico en RAM.
Salida JSONL versionada para un futuro consumidor de solo lectura en Mac.
"""

import argparse
import json
import sys
import time

from arm_simulation import ArmSimulation, SIM_ARMED


SCHEMA = "brazo.jetson.sim.telemetry"
SCHEMA_VERSION = 1
SOURCE = "jetson_simulation"
STEP_S = 0.1
STEPS_PER_DIRECTION = 5


def make_frame(simulator, sequence):
    """Construye un snapshot independiente, sin ningun acceso al hardware."""
    if type(sequence) is not int or sequence < 0:
        raise ValueError("sequence debe ser un entero no negativo")

    snapshot = simulator.snapshot()
    if snapshot["hardware_enabled"] is not False:
        raise RuntimeError("Telemetria rechazada: hardware_enabled")
    if snapshot["mode"] != "simulation_only":
        raise RuntimeError("Telemetria rechazada: modo no simulado")

    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE,
        "sequence": sequence,
        "mode": snapshot["mode"],
        "state": snapshot["state"],
        "fault_reason": snapshot["fault_reason"],
        "hardware_enabled": False,
        "servos": snapshot["servos"],
    }


def run_demo(clock=None, sleep=None, output=None):
    """Emite 13 tramas de demo: Base 90->125->90, luego DISARMED.

    Los parametros opcionales permiten pruebas deterministas sin esperar.
    El flujo termina por si solo; no procesa ordenes remotas ni stdin.
    """
    clock = time.monotonic if clock is None else clock
    sleep = time.sleep if sleep is None else sleep
    output = sys.stdout if output is None else output
    simulator = ArmSimulation(clock=clock)
    sequence = 0

    def emit():
        frame = make_frame(simulator, sequence)
        output.write(json.dumps(frame, sort_keys=True, separators=(",", ":")))
        output.write("\n")
        output.flush()

    emit()  # DISARMED inicial
    simulator.arm_simulation()
    sequence += 1
    emit()  # SIM_ARMED matematico, nunca hardware

    try:
        for target in (125, 90):
            simulator.set_target(1, target)
            for _ in range(STEPS_PER_DIRECTION):
                sleep(STEP_S)
                simulator.heartbeat()
                simulator.tick()
                sequence += 1
                emit()
    finally:
        if simulator.state == SIM_ARMED:
            simulator.disarm_simulation()

    sequence += 1
    emit()  # DISARMED final, objetivo = posicion actual
    return sequence + 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Telemetria JSONL de DEMO simulada, sin hardware ni red"
    )
    parser.add_argument(
        "--demo", action="store_true", help="emite 13 tramas y termina"
    )
    args = parser.parse_args(argv)
    if not args.demo:
        parser.error("Solo disponible con --demo (sin motores)")
    run_demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
