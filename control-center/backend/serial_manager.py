"""Transporte serial robusto y parser del protocolo del ESP32."""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # Permite ejecutar simulacion sin dependencias de hardware.
    serial = None
    list_ports = None

from config import SERIAL_BAUD, SERIAL_PORT
from robot_state import RobotState


STATUS_RE = re.compile(
    r"^\d+\)\s+(\w+)\s+\|\s+PCA ch=(\d+)\s+\|\s+"
    r"current=(-?\d+)\s+\|\s+target=(-?\d+)\s+\|\s+"
    r"min=(-?\d+)\s+\|\s+max=(-?\d+)$"
)

PROTOCOL_EVENTS = (
    ("saludo iniciado", "saludo_started"),
    ("saludo terminado", "saludo_finished"),
    ("rutina iniciada", "rutina_started"),
    ("rutina terminada", "rutina_finished"),
    ("coreografia detenida", "choreo_stopped"),
    ("OK -> home", "home"),
)


def discover_serial_port(preferred: str = "") -> str:
    """Resuelve el puerto indicado o el adaptador USB serial mas probable."""
    if preferred:
        return preferred

    if list_ports is None:
        raise RuntimeError("Falta pyserial; instala requirements.txt para usar el ESP32.")
    ports = list(list_ports.comports())
    if not ports:
        raise RuntimeError(
            "No se encontro ningun puerto serial. Define ROBOT_SERIAL_PORT si el ESP32 esta conectado."
        )

    keywords = ("usbserial", "usbmodem", "cp210", "ch340", "uart", "esp32")
    ranked = sorted(
        ports,
        key=lambda port: not any(
            token in f"{port.device} {port.description} {port.manufacturer}".lower()
            for token in keywords
        ),
    )
    return ranked[0].device


class SerialManager:
    def __init__(
        self,
        state: RobotState,
        port: str = SERIAL_PORT,
        baud: int = SERIAL_BAUD,
        event_handler: Callable[[str], None] | None = None,
    ):
        self.state = state
        self.port = port
        self.baud = baud
        self.event_handler = event_handler
        self.ser: serial.Serial | None = None
        self._reader_thread: threading.Thread | None = None
        self._running = threading.Event()
        self._inside_status_block = False
        self._write_lock = threading.Lock()

    @property
    def connected(self) -> bool:
        return bool(self.ser and self.ser.is_open)

    def connect(self) -> str:
        if serial is None:
            raise RuntimeError("Falta pyserial; instala requirements.txt para usar el ESP32.")
        resolved_port = discover_serial_port(self.port)
        ser = serial.Serial(resolved_port, self.baud, timeout=0.05)
        try:
            time.sleep(2.0)
            ser.reset_input_buffer()
        except Exception:
            ser.close()
            raise

        self.port = resolved_port
        self.ser = ser
        self._running.set()
        self._reader_thread = threading.Thread(
            target=self._read_loop,
            name="robot-serial-reader",
            daemon=True,
        )
        self._reader_thread.start()
        self.state.set_connected(True, self.port)
        self.state.add_log(f"[SERIAL] conectado a {self.port} @ {self.baud}")
        return self.port

    def disconnect(self) -> None:
        self._running.clear()
        ser, self.ser = self.ser, None
        if ser:
            try:
                ser.close()
            except Exception:
                pass
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=0.5)
        self._reader_thread = None
        self.state.set_connected(False, None)

    def send(self, cmd: str) -> bool:
        ser = self.ser
        if not ser or not ser.is_open:
            return False

        try:
            with self._write_lock:
                ser.write((cmd.strip() + "\n").encode("utf-8"))
                ser.flush()
            if cmd != "status":
                self.state.add_log(f">> {cmd}")
            return True
        except Exception as exc:
            self.state.add_log(f"[SERIAL ERROR] {exc}")
            self.state.set_error(str(exc))
            self.state.set_connected(False, None)
            return False

    def _emit(self, event: str) -> None:
        if self.event_handler:
            try:
                self.event_handler(event)
            except Exception as exc:  # El lector serial nunca debe morir por un callback.
                self.state.add_log(f"[PROTOCOLO ERROR] {exc}")

    def _read_loop(self) -> None:
        while self._running.is_set():
            ser = self.ser
            if not ser:
                break
            try:
                raw = ser.readline()
                if not raw:
                    continue

                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                if line == "---- STATUS ----":
                    self._inside_status_block = True
                    continue
                if line == "----------------":
                    self._inside_status_block = False
                    continue

                if self._inside_status_block:
                    match = STATUS_RE.match(line)
                    if match:
                        name, channel, current, target, minimum, maximum = match.groups()
                        self.state.update_from_status_line(
                            servo_name=name,
                            pca_channel=int(channel),
                            current=int(current),
                            target=int(target),
                            min_angle=int(minimum),
                            max_angle=int(maximum),
                        )
                    continue

                # El firmware responde OK a cada movimiento. Mostrar cada ACK
                # llenaba la consola y obligaba al WebSocket a reenviar el estado.
                if line != "OK":
                    self.state.add_log(f"ESP32: {line}")

                for needle, event in PROTOCOL_EVENTS:
                    if needle in line:
                        self._emit(event)
                        break

            except Exception as exc:
                if self._running.is_set():
                    self.state.add_log(f"[SERIAL READ ERROR] {exc}")
                    self.state.set_error(str(exc))
                    self.state.set_connected(False, None)
                break
