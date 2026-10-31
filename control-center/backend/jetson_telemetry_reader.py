"""Validador pasivo de telemetria matematica Jetson Nano -> Mac.

Lee JSON Lines EXCLUSIVAMENTE desde stdin. No abre conexiones de red,
no envia comandos SSH, WebSocket ni serial, no accede a I2C/GPIO/PWM,
no controla el dashboard. El stdout se publica solo tras validar la
demostracion completa; fallar cerrado ante tramas inesperadas.

El transporte externo (SSH autenticado) sera establecido por el
operador mediante una tuberia de shell. Python 3.12 en Mac.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Iterable
from typing import Any

from config import SERVO_SPECS


SCHEMA = "brazo.jetson.sim.telemetry"
VERSION = 1
SOURCE = "jetson_simulation"
DEMO_FRAMES = 13
MAX_FRAME_CHARS = 16384
STATES = {"DISARMED", "SIM_ARMED", "FAULT"}
FRAME_KEYS = {
    "schema", "schema_version", "source", "sequence", "mode", "state",
    "fault_reason", "hardware_enabled", "servos",
}
SERVO_KEYS = {"id", "pca_channel", "current", "target", "min", "max", "measured"}


class TelemetryValidationError(ValueError):
    """No confiar en una trama que incumple el contrato de simulacion."""


def _reject_json_constant(token: str) -> None:
    raise TelemetryValidationError(f"Constante JSON no valida: {token}")


def _bounded_number(value: Any, lower: int, upper: int, label: str) -> float:
    if type(value) not in (int, float):
        raise TelemetryValidationError(f"{label}: se esperaba un numero")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise TelemetryValidationError(f"{label}: valor no representable") from exc
    if not math.isfinite(number) or not lower <= number <= upper:
        raise TelemetryValidationError(f"{label}: fuera de rango o no finito")
    return number


def validate_frame(frame: Any, expected_sequence: int) -> dict[str, Any]:
    """Rechaza fuentes, esquemas, estados y servos inesperados.

    No infiere posicion real: measured debe ser False sin excepciones.
    """
    if not isinstance(frame, dict) or set(frame) != FRAME_KEYS:
        raise TelemetryValidationError("Estructura de trama no permitida")
    if frame["schema"] != SCHEMA or type(frame["schema_version"]) is not int:
        raise TelemetryValidationError("Esquema o version incorrectos")
    if frame["schema_version"] != VERSION or frame["source"] != SOURCE:
        raise TelemetryValidationError("Version o fuente no autorizadas")
    if type(frame["sequence"]) is not int or frame["sequence"] != expected_sequence:
        raise TelemetryValidationError("Secuencia faltante, repetida o desordenada")
    if frame["mode"] != "simulation_only":
        raise TelemetryValidationError("Solo se aceptan datos simulados")
    if frame["hardware_enabled"] is not False:
        raise TelemetryValidationError("Se rechaza telemetria con hardware habilitado")
    if frame["state"] not in STATES:
        raise TelemetryValidationError("Estado no reconocido")
    reason = frame["fault_reason"]
    if reason is not None and (not isinstance(reason, str) or len(reason) > 200):
        raise TelemetryValidationError("Motivo de fallo invalido")

    servos = frame["servos"]
    names = {spec.name for spec in SERVO_SPECS}
    if not isinstance(servos, dict) or set(servos) != names:
        raise TelemetryValidationError("El contrato requiere seis articulaciones")

    for spec in SERVO_SPECS:
        servo = servos[spec.name]
        if not isinstance(servo, dict) or set(servo) != SERVO_KEYS:
            raise TelemetryValidationError(f"{spec.name}: campos invalidos")
        if type(servo["id"]) is not int or servo["id"] != spec.servo_id:
            raise TelemetryValidationError(f"{spec.name}: ID no coincide")
        if type(servo["pca_channel"]) is not int or servo["pca_channel"] != spec.pca_channel:
            raise TelemetryValidationError(f"{spec.name}: canal no coincide")
        if (
            type(servo["min"]) is not int
            or type(servo["max"]) is not int
            or (servo["min"], servo["max"]) != (spec.min_angle, spec.max_angle)
        ):
            raise TelemetryValidationError(f"{spec.name}: limites no coinciden")
        if servo["measured"] is not False:
            raise TelemetryValidationError(f"{spec.name}: no es posicion medida")
        _bounded_number(servo["current"], spec.min_angle, spec.max_angle,
                        f"{spec.name}.current")
        _bounded_number(servo["target"], spec.min_angle, spec.max_angle,
                        f"{spec.name}.target")

    return frame


def read_demo_stream(lines: Iterable[str]) -> list[dict[str, Any]]:
    """Acepta solo 13 tramas del demo predecible; no comandos remotos."""
    frames: list[dict[str, Any]] = []
    for raw in lines:
        if len(frames) >= DEMO_FRAMES:
            raise TelemetryValidationError("Tramas adicionales inesperadas")
        if not isinstance(raw, str) or not raw.strip() or len(raw) > MAX_FRAME_CHARS:
            raise TelemetryValidationError("Linea vacia o demasiado grande")
        try:
            parsed = json.loads(raw, parse_constant=_reject_json_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            raise TelemetryValidationError(f"JSON invalido: {exc}") from exc
        frame = validate_frame(parsed, len(frames))
        frames.append(frame)

    if len(frames) != DEMO_FRAMES:
        raise TelemetryValidationError(
            f"Flujo incompleto: {len(frames)}/{DEMO_FRAMES} tramas"
        )

    for index, frame in enumerate(frames):
        expected_state = "DISARMED" if index in (0, DEMO_FRAMES - 1) else "SIM_ARMED"
        if frame["state"] != expected_state or frame["fault_reason"] is not None:
            raise TelemetryValidationError(f"Estado inesperado en secuencia {index}")

    for spec in SERVO_SPECS:
        first = frames[0]["servos"][spec.name]
        last = frames[-1]["servos"][spec.name]
        if (
            first["current"] != spec.home or first["target"] != spec.home
            or last["current"] != spec.home or last["target"] != spec.home
        ):
            raise TelemetryValidationError(f"{spec.name}: la demo no regreso a Home")

    angles = [frame["servos"]["base"]["current"] for frame in frames]
    if (
        not math.isclose(max(angles), 125.0, abs_tol=0.15)
        or any(right < left for left, right in zip(angles[1:6], angles[2:7]))
        or any(right > left for left, right in zip(angles[6:11], angles[7:12]))
    ):
        raise TelemetryValidationError("Trayectoria simulada de Base inesperada")

    return frames


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Valida telemetria Jetson simulada leida de stdin, sin control"
    )
    parser.add_argument(
        "--stdin-demo", action="store_true",
        help="validar 13 tramas JSONL procedentes del demo Jetson"
    )
    args = parser.parse_args(argv)
    if not args.stdin_demo:
        parser.error("Usar exclusivamente --stdin-demo")
    try:
        frames = read_demo_stream(sys.stdin)
    except (TelemetryValidationError, UnicodeError) as exc:
        print(f"TELEMETRIA RECHAZADA: {exc}", file=sys.stderr)
        return 1

    angles = [frame["servos"]["base"]["current"] for frame in frames]
    print("=== TELEMETRIA JETSON SIMULADA VALIDADA EN MAC ===")
    print("Origen:", SOURCE, "| version:", VERSION)
    print("Tramas:", len(frames))
    print("Base (grados):", " -> ".join(f"{angle:.1f}" for angle in angles))
    print("Estado final:", frames[-1]["state"])
    print("Hardware habilitado: False | Posicion medida: False")
    print("MAC_JETSON_TELEMETRY_READONLY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
