import time

import pygame

from config import (
    BASE_RATE,
    CALIBRATION_SECONDS,
    CODO_RATE,
    DEADZONE,
    GARRA_RATE,
    HOMBRO_RATE,
    HOME,
    LIMITS,
    MUNECA1_RATE,
    MUNECA2_RATE,
)


def clamp(value, low, high):
    return max(low, min(high, value))


def normalize_axis(raw, center, deadzone=DEADZONE):
    if raw >= center:
        span = max(0.001, 1.0 - center)
        value = (raw - center) / span
    else:
        span = max(0.001, center + 1.0)
        value = (raw - center) / span

    value = clamp(value, -1.0, 1.0)

    if abs(value) < deadzone:
        return 0.0

    if value > 0:
        value = (value - deadzone) / (1.0 - deadzone)
    else:
        value = (value + deadzone) / (1.0 - deadzone)

    return clamp(value, -1.0, 1.0)


class JoystickManager:
    def __init__(self, state, serial_manager):
        self.state = state
        self.serial_manager = serial_manager

        pygame.init()
        pygame.joystick.init()

        count = pygame.joystick.get_count()
        print(f"[JOYSTICK] detectados: {count}")
        if count == 0:
            raise RuntimeError("No se detecto ningun joystick.")

        self.js = pygame.joystick.Joystick(0)
        self.js.init()
        self.state.set_joystick_connected(True)

        print("[JOYSTICK] nombre:", self.js.get_name())
        print("[JOYSTICK] ejes:", self.js.get_numaxes())
        print("[JOYSTICK] botones:", self.js.get_numbuttons())
        print("[JOYSTICK] hats:", self.js.get_numhats())

        self.axis_centers = self._calibrate()
        self.targets = {k: float(v) for k, v in HOME.items()}
        self.last_sent = {k: None for k in HOME.keys()}
        self.last_buttons = {}
        self.manual_enabled = True

        print("\n[JOYSTICK] mapeo actual:")
        print("  Axis 0                 -> base")
        print("  Axis 1                 -> hombro")
        print("  Button 2               -> codo hacia abajo")
        print("  Button 3               -> codo hacia arriba")
        print("  Hat izquierda/derecha  -> muneca1 (sube/baja garra)")
        print("  Hat arriba/abajo       -> muneca2 (gira garra)")
        print("  Button 0 (gatillo)     -> cerrar garra")
        print("  Button 1               -> abrir garra")
        print("  Button 4               -> home")
        print("  Button 5               -> saludo")
        print("  Button 6               -> stop")
        print("  Button 7               -> salir\n")

    def _calibrate(self):
        print(f"[JOYSTICK] calibrando durante {CALIBRATION_SECONDS:.1f} s...")
        axis_count = self.js.get_numaxes()
        axis_sums = [0.0] * axis_count
        samples = 0

        start_cal = time.time()
        while time.time() - start_cal < CALIBRATION_SECONDS:
            pygame.event.pump()
            for i in range(axis_count):
                axis_sums[i] += self.js.get_axis(i)
            samples += 1
            time.sleep(0.01)

        centers = [s / max(1, samples) for s in axis_sums]

        print("[JOYSTICK] centros:")
        for i, c in enumerate(centers):
            print(f"  axis {i}: {c:.3f}")

        return centers

    def force_sync_targets(self):
        for sid in self.targets:
            self.last_sent[sid] = None

    def tick(self, dt: float):
        pygame.event.pump()

        ax0 = normalize_axis(self.js.get_axis(0), self.axis_centers[0]) if self.js.get_numaxes() > 0 else 0.0
        ax1 = normalize_axis(self.js.get_axis(1), self.axis_centers[1]) if self.js.get_numaxes() > 1 else 0.0

        hat_x, hat_y = (0, 0)
        if self.js.get_numhats() > 0:
            hat_x, hat_y = self.js.get_hat(0)

        b0 = self.js.get_button(0) if self.js.get_numbuttons() > 0 else 0
        b1 = self.js.get_button(1) if self.js.get_numbuttons() > 1 else 0
        b2 = self.js.get_button(2) if self.js.get_numbuttons() > 2 else 0
        b3 = self.js.get_button(3) if self.js.get_numbuttons() > 3 else 0
        b4 = self.js.get_button(4) if self.js.get_numbuttons() > 4 else 0
        b5 = self.js.get_button(5) if self.js.get_numbuttons() > 5 else 0
        b6 = self.js.get_button(6) if self.js.get_numbuttons() > 6 else 0
        b7 = self.js.get_button(7) if self.js.get_numbuttons() > 7 else 0

        self.state.set_joystick_state(
            axis0=ax0,
            axis1=ax1,
            hat=(hat_x, hat_y),
            buttons=[b0, b1, b2, b3, b4, b5, b6, b7],
        )

        if b4 and not self.last_buttons.get("b4", 0):
            self.serial_manager.send("home")
            self.targets = {k: float(v) for k, v in HOME.items()}
            self.manual_enabled = True
            self.force_sync_targets()

        if b5 and not self.last_buttons.get("b5", 0):
            self.serial_manager.send("saludo")
            self.manual_enabled = False
            self.state.set_mode("saludo")

        if b6 and not self.last_buttons.get("b6", 0):
            self.serial_manager.send("stop")
            self.manual_enabled = True
            self.targets = {k: float(v) for k, v in HOME.items()}
            self.force_sync_targets()
            self.state.set_mode("manual")

        if b7 and not self.last_buttons.get("b7", 0):
            raise KeyboardInterrupt("Salida solicitada desde button 7")

        self.last_buttons["b4"] = b4
        self.last_buttons["b5"] = b5
        self.last_buttons["b6"] = b6
        self.last_buttons["b7"] = b7

        if self.manual_enabled:
            # Base
            self.targets[1] += (-ax0) * BASE_RATE * dt

            # Hombro
            self.targets[2] += (-ax1) * HOMBRO_RATE * dt

            # Codo / antebrazo
            if b2 and not b3:
                self.targets[3] -= CODO_RATE * dt
            elif b3 and not b2:
                self.targets[3] += CODO_RATE * dt

            # MUÑECA 1 = subir / bajar garra
            # ahora con hat izquierda/derecha
            self.targets[4] += hat_x * MUNECA1_RATE * dt

            # MUÑECA 2 = girar garra
            # ahora con hat arriba/abajo
            self.targets[5] += (-hat_y) * MUNECA2_RATE * dt

            # Garra
            if b0 and not b1:
                self.targets[6] -= GARRA_RATE * dt  # cerrar
            elif b1 and not b0:
                self.targets[6] += GARRA_RATE * dt  # abrir

            for sid in self.targets:
                lo, hi = LIMITS[sid]
                self.targets[sid] = clamp(self.targets[sid], lo, hi)