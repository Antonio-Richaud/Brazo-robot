"""Configuracion compartida del Control Center.

Los valores que dependen de la computadora se leen desde variables de entorno.
La geometria segura del brazo se mantiene en una sola tabla para que el backend
no repita Home, limites y canales en varios archivos.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class ServoSpec:
    servo_id: int
    name: str
    pca_channel: int
    home: int
    min_angle: int
    max_angle: int
    rate_deg_s: float


SERVO_SPECS = (
    ServoSpec(1, "base", 0, 90, 10, 170, 70.0),
    ServoSpec(2, "hombro", 1, 50, 15, 165, 55.0),
    ServoSpec(3, "codo", 2, 165, 15, 165, 70.0),
    ServoSpec(4, "muneca1", 3, 10, 10, 170, 90.0),
    ServoSpec(5, "muneca2", 4, 170, 10, 170, 90.0),
    ServoSpec(6, "garra", 5, 40, 20, 140, 90.0),
)

SERVO_BY_ID = {spec.servo_id: spec for spec in SERVO_SPECS}
SERVO_NAMES = {spec.servo_id: spec.name for spec in SERVO_SPECS}
HOME = {spec.servo_id: spec.home for spec in SERVO_SPECS}
LIMITS = {
    spec.servo_id: (spec.min_angle, spec.max_angle)
    for spec in SERVO_SPECS
}

SERIAL_PORT = os.getenv("ROBOT_SERIAL_PORT", "").strip()
SERIAL_BAUD = _env_int("ROBOT_SERIAL_BAUD", 115200)

CALIBRATION_SECONDS = _env_float("ROBOT_JOYSTICK_CALIBRATION", 2.0)
DEADZONE = _env_float("ROBOT_JOYSTICK_DEADZONE", 0.08)

# Conservadores para no saturar al ESP32 ni llenar el log con ACKs.
STATUS_POLL_INTERVAL = _env_float("ROBOT_STATUS_INTERVAL", 0.60)
SEND_INTERVAL = _env_float("ROBOT_SEND_INTERVAL", 0.08)
LOOP_SLEEP = _env_float("ROBOT_LOOP_SLEEP", 0.015)
MAX_CONTROL_DT = _env_float("ROBOT_MAX_CONTROL_DT", 0.05)

WS_HOST = os.getenv("ROBOT_WS_HOST", "127.0.0.1")
WS_PORT = _env_int("ROBOT_WS_PORT", 8765)
WS_PUBLISH_INTERVAL = _env_float("ROBOT_WS_INTERVAL", 0.05)

REALSENSE_SERIAL = os.getenv("REALSENSE_SERIAL", "926522071007").strip()
REALSENSE_MODEL = "Intel RealSense D435i"
REALSENSE_ENABLE_IMU = os.getenv("REALSENSE_ENABLE_IMU", "0").lower() in {"1", "true", "yes"}
REALSENSE_ENABLE_COLOR = os.getenv("REALSENSE_ENABLE_COLOR", "0").lower() in {"1", "true", "yes"}
PERCEPTION_RATE_HZ = _env_float("ROBOT_PERCEPTION_HZ", 8.0)
PERCEPTION_MAX_POINTS = _env_int("ROBOT_PERCEPTION_MAX_POINTS", 1600)
PERCEPTION_REMOTE_URL = os.getenv(
    "ROBOT_PERCEPTION_URL", "ws://jetson-nano.local:8766"
).strip()

# Alias legibles conservados para el mapeo del joystick.
BASE_RATE = SERVO_BY_ID[1].rate_deg_s
HOMBRO_RATE = SERVO_BY_ID[2].rate_deg_s
CODO_RATE = SERVO_BY_ID[3].rate_deg_s
MUNECA1_RATE = SERVO_BY_ID[4].rate_deg_s
MUNECA2_RATE = SERVO_BY_ID[5].rate_deg_s
GARRA_RATE = SERVO_BY_ID[6].rate_deg_s
