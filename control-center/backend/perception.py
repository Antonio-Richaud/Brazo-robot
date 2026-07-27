"""Nodo opcional de percepcion para simulacion y RealSense D435i.

La percepcion nunca controla servos directamente. Publica puntos y metricas en
el marco del robot; una futura capa de planeacion podra consumirlos con sus
propias barreras de seguridad.
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
from dataclasses import dataclass
from typing import Any

from config import (
    PERCEPTION_MAX_POINTS,
    PERCEPTION_RATE_HZ,
    PERCEPTION_REMOTE_URL,
    REALSENSE_ENABLE_IMU,
    REALSENSE_ENABLE_COLOR,
    REALSENSE_MODEL,
    REALSENSE_SERIAL,
)


@dataclass
class PerceptionFrame:
    points: list[list[float]]
    closest_distance_m: float | None
    obstacles: list[dict[str, Any]]
    calibrated: bool
    coordinate_frame: str = "robot_base"


class PerceptionWorker:
    def __init__(
        self,
        state,
        source: str = "off",
        serial: str = REALSENSE_SERIAL,
        rate_hz: float = PERCEPTION_RATE_HZ,
        max_points: int = PERCEPTION_MAX_POINTS,
        remote_url: str = PERCEPTION_REMOTE_URL,
    ):
        self.state = state
        self.source = source
        self.serial = serial
        self.rate_hz = max(1.0, rate_hz)
        self.max_points = max(100, max_points)
        self.remote_url = remote_url
        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self._frame_id = 0
        self._provider = None

    def start(self) -> None:
        if self.source == "off":
            self.state.update_perception(
                {"enabled": False, "source": "off", "status": "inactive", "points": []}
            )
            return
        if self.source == "simulated":
            self._provider = SimulatedPerceptionProvider(self.max_points)
        elif self.source == "remote":
            self._provider = RemotePerceptionProvider(self.remote_url)
        else:
            self._provider = RealSenseProvider(self.serial, self.max_points)
        self._running.set()
        self._thread = threading.Thread(
            target=self._run,
            name="robot-perception",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._provider:
            self._provider.close()

    def _run(self) -> None:
        interval = 1.0 / self.rate_hz
        measured_fps = 0.0
        last_frame_at = None
        try:
            self._provider.open()
            self.state.add_log(f"[PERCEPCION] fuente {self.source} lista")
            while self._running.is_set():
                started = time.monotonic()
                frame = self._provider.capture()
                now = time.monotonic()
                if last_frame_at is not None:
                    instant_fps = 1.0 / max(0.001, now - last_frame_at)
                    measured_fps = instant_fps if measured_fps == 0 else measured_fps * 0.8 + instant_fps * 0.2
                last_frame_at = now
                self._frame_id += 1
                self.state.update_perception(
                    {
                        "enabled": True,
                        "source": self.source,
                        "status": "streaming",
                        "model": REALSENSE_MODEL,
                        "serial": self.serial,
                        "coordinate_frame": frame.coordinate_frame,
                        "calibrated": frame.calibrated,
                        "frame_id": self._frame_id,
                        "fps": round(measured_fps, 1),
                        "point_count": len(frame.points),
                        "closest_distance_m": frame.closest_distance_m,
                        "points": frame.points,
                        "obstacles": frame.obstacles,
                        "error": None,
                    }
                )
                remaining = interval - (time.monotonic() - started)
                if remaining > 0:
                    time.sleep(remaining)
        except Exception as exc:
            self.state.add_log(f"[PERCEPCION ERROR] {exc}")
            self.state.update_perception(
                {
                    "enabled": False,
                    "source": self.source,
                    "status": "error",
                    "error": str(exc),
                    "points": [],
                    "point_count": 0,
                }
            )


class SimulatedPerceptionProvider:
    def __init__(self, max_points: int):
        self.max_points = max_points
        self.started_at = time.monotonic()
        self._base_points = self._make_scene()

    def open(self) -> None:
        return

    def close(self) -> None:
        return

    def capture(self) -> PerceptionFrame:
        phase = (time.monotonic() - self.started_at) * 0.55
        moving_x = 1.4 + math.sin(phase) * 0.28
        points = [point[:] for point in self._base_points]
        for _ in range(150):
            points.append(
                [
                    round(moving_x + random.uniform(-0.16, 0.16), 3),
                    round(random.uniform(0.05, 0.55), 3),
                    round(-0.7 + random.uniform(-0.16, 0.16), 3),
                ]
            )
        points = points[: self.max_points]
        return PerceptionFrame(
            points=points,
            closest_distance_m=round(max(0.1, moving_x - 0.16), 2),
            obstacles=[
                {
                    "id": "sim-box",
                    "label": "objeto simulado",
                    "center": [round(moving_x, 3), 0.3, -0.7],
                    "size": [0.32, 0.5, 0.32],
                    "confidence": 1.0,
                }
            ],
            calibrated=True,
        )

    def _make_scene(self) -> list[list[float]]:
        points: list[list[float]] = []
        for x_index in range(-16, 17):
            for z_index in range(-16, 17):
                if (x_index + z_index) % 2:
                    continue
                points.append([round(x_index * 0.12, 3), 0.0, round(z_index * 0.12, 3)])
        return points


class RealSenseProvider:
    """Captura directa con pyrealsense2; la importacion es deliberadamente lazy."""

    def __init__(self, serial: str, max_points: int):
        self.serial = serial
        self.max_points = max_points
        self.rs = None
        self.np = None
        self.pipeline = None
        self.pointcloud = None

    def open(self) -> None:
        try:
            import numpy as np
            import pyrealsense2 as rs
        except ImportError as exc:
            raise RuntimeError(
                "Falta pyrealsense2/numpy. Instala requirements-realsense.txt en un entorno Python compatible."
            ) from exc

        self.rs, self.np = rs, np
        self.pipeline = rs.pipeline()
        config = rs.config()
        if self.serial:
            config.enable_device(self.serial)
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        if REALSENSE_ENABLE_COLOR:
            config.enable_stream(rs.stream.color, 640, 480, rs.format.rgb8, 30)
        # En macOS el stream IMU ha sido historicamente menos estable. Se activa
        # de forma explicita cuando el nodo corre en una plataforma validada.
        if REALSENSE_ENABLE_IMU:
            config.enable_stream(rs.stream.accel, rs.format.motion_xyz32f, 63)
            config.enable_stream(rs.stream.gyro, rs.format.motion_xyz32f, 200)
        self.pipeline.start(config)
        self.pointcloud = rs.pointcloud()

    def close(self) -> None:
        if self.pipeline:
            try:
                self.pipeline.stop()
            except RuntimeError:
                pass

    def capture(self) -> PerceptionFrame:
        frames = self.pipeline.wait_for_frames(1500)
        depth = frames.get_depth_frame()
        if not depth:
            raise RuntimeError("La D435i no entrego un frame de profundidad.")

        rs_points = self.pointcloud.calculate(depth)
        vertices = self.np.asanyarray(rs_points.get_vertices()).view(self.np.float32).reshape(-1, 3)
        finite = self.np.isfinite(vertices).all(axis=1)
        valid = vertices[finite]
        valid = valid[(valid[:, 2] > 0.15) & (valid[:, 2] < 3.5)]
        if len(valid) > self.max_points:
            stride = max(1, len(valid) // self.max_points)
            valid = valid[::stride][: self.max_points]

        # RealSense: x derecha, y abajo, z frente. La UI usa y arriba.
        converted = self.np.column_stack((valid[:, 0], -valid[:, 1], -valid[:, 2]))
        converted = self.np.round(converted, 3)
        closest = float(valid[:, 2].min()) if len(valid) else None
        return PerceptionFrame(
            points=converted.tolist(),
            closest_distance_m=round(closest, 2) if closest else None,
            obstacles=[],
            # Hasta medir la transformacion camara->base no se usa para autonomia.
            calibrated=False,
            coordinate_frame="camera",
        )


class RemotePerceptionProvider:
    """Cliente ligero para recibir la nube procesada por una Jetson."""

    def __init__(self, url: str):
        self.url = url
        self.connection = None

    def open(self) -> None:
        try:
            from websockets.sync.client import connect
        except ImportError as exc:
            raise RuntimeError("La percepcion remota requiere websockets>=14.") from exc
        self.connection = connect(self.url, open_timeout=4, close_timeout=1)

    def close(self) -> None:
        if self.connection:
            self.connection.close()

    def capture(self) -> PerceptionFrame:
        message = self.connection.recv(timeout=3)
        payload = json.loads(message)
        return PerceptionFrame(
            points=payload.get("points", []),
            closest_distance_m=payload.get("closest_distance_m"),
            obstacles=payload.get("obstacles", []),
            calibrated=bool(payload.get("calibrated", False)),
            coordinate_frame=payload.get("coordinate_frame", "camera"),
        )
