import re
import threading
import time

import serial

from config import SERIAL_BAUD, SERIAL_PORT
from robot_state import RobotState


STATUS_RE = re.compile(
    r"^\d+\)\s+(\w+)\s+\|\s+PCA ch=(\d+)\s+\|\s+current=(\d+)\s+\|\s+target=(\d+)\s+\|\s+min=(\d+)\s+\|\s+max=(\d+)$"
)


class SerialManager:
    def __init__(self, state: RobotState, port: str = SERIAL_PORT, baud: int = SERIAL_BAUD):
        self.state = state
        self.port = port
        self.baud = baud
        self.ser = None
        self._reader_thread = None
        self._running = False
        self._inside_status_block = False
        self._write_lock = threading.Lock()

    def connect(self):
        self.ser = serial.Serial(self.port, self.baud, timeout=0.05)
        time.sleep(2.0)
        self.ser.reset_input_buffer()
        self._running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        self.state.set_connected(True, self.port)
        self.state.add_log(f"[SERIAL] conectado a {self.port} @ {self.baud}")
        print(f"[SERIAL] conectado a {self.port} @ {self.baud}")

    def disconnect(self):
        self._running = False
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.state.set_connected(False, None)
        self.state.add_log("[SERIAL] desconectado")
        print("[SERIAL] desconectado")

    def send(self, cmd: str):
        if not self.ser:
            return

        try:
            with self._write_lock:
                self.ser.write((cmd + "\n").encode("utf-8"))
                self.ser.flush()

            if cmd != "status":
                self.state.add_log(f">> {cmd}")
                print(f">> {cmd}")
        except Exception as e:
            self.state.add_log(f"[SERIAL ERROR] {e}")
            print(f"[SERIAL ERROR] {e}")

    def _read_loop(self):
        while self._running and self.ser:
            try:
                raw = self.ser.readline()
                if not raw:
                    continue

                line = raw.decode("utf-8", errors="ignore").strip()
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
                        servo_name, pca_channel, current, target, min_angle, max_angle = match.groups()
                        self.state.update_from_status_line(
                            servo_name=servo_name,
                            pca_channel=int(pca_channel),
                            current=int(current),
                            target=int(target),
                            min_angle=int(min_angle),
                            max_angle=int(max_angle),
                        )
                    continue

                self.state.add_log(f"ESP32: {line}")
                print(f"ESP32: {line}")

                if "saludo iniciado" in line:
                    self.state.set_mode("saludo")
                elif "saludo terminado" in line:
                    self.state.set_mode("manual")
                elif "coreografia detenida" in line:
                    self.state.set_mode("manual")
                elif "OK -> home" in line:
                    self.state.set_mode("manual")

            except Exception as e:
                self.state.add_log(f"[SERIAL READ ERROR] {e}")
                print(f"[SERIAL READ ERROR] {e}")
                time.sleep(0.2)