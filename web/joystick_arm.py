import time
import pygame
import serial

PORT = "/dev/cu.usbserial-10"
BAUD = 115200

CALIBRATION_SECONDS = 2.0
SEND_INTERVAL = 0.06
DEADZONE = 0.08

BASE_RATE = 70.0
HOMBRO_RATE = 55.0
CODO_RATE = 70.0
MUNECA1_RATE = 90.0
MUNECA2_RATE = 90.0
GARRA_RATE = 90.0

HOME = {
    1: 90,
    2: 50,
    3: 165,
    4: 10,
    5: 170,
    6: 40
}

LIMITS = {
    1: (10, 170),
    2: (15, 165),
    3: (15, 165),
    4: (10, 170),
    5: (10, 170),
    6: (20, 140)
}

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

def send_cmd(ser, cmd):
    ser.write((cmd + "\n").encode("utf-8"))
    print(">>", cmd)

def read_serial_lines(ser):
    lines = []
    while True:
        line = ser.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="ignore").strip()
        if text:
            lines.append(text)
    return lines

pygame.init()
pygame.joystick.init()

count = pygame.joystick.get_count()
print(f"Joysticks detectados: {count}")

if count == 0:
    raise SystemExit("No se detecto ningun joystick.")

js = pygame.joystick.Joystick(0)
js.init()

print("Joystick:", js.get_name())
print("Ejes:", js.get_numaxes())
print("Botones:", js.get_numbuttons())
print("Hats:", js.get_numhats())

print("\nDeja el joystick completamente quieto...")
print(f"Calibrando durante {CALIBRATION_SECONDS:.1f} segundos.\n")

axis_count = js.get_numaxes()
axis_sums = [0.0] * axis_count
samples = 0

start_cal = time.time()
while time.time() - start_cal < CALIBRATION_SECONDS:
    pygame.event.pump()
    for i in range(axis_count):
        axis_sums[i] += js.get_axis(i)
    samples += 1
    time.sleep(0.01)

axis_centers = [s / max(1, samples) for s in axis_sums]

print("Centros calibrados:")
for i, c in enumerate(axis_centers):
    print(f"  axis {i}: {c:.3f}")

print("\nControles:")
print("  Palanca X (axis 0)     -> base")
print("  Palanca Y (axis 1)     -> hombro")
print("  Boton 3 (button 2)     -> codo hacia arriba")
print("  Boton 4 (button 3)     -> codo hacia abajo")
print("  Hat izquierda/derecha  -> muneca1")
print("  Hat arriba/abajo       -> muneca2")
print("  Gatillo (button 0)     -> cerrar garra")
print("  Boton 2 (button 1)     -> abrir garra")
print("  Rapido 1 (button 4)    -> home")
print("  Rapido 2 (button 5)    -> saludo")
print("  Rapido 3 (button 6)    -> stop")
print("  Rapido 4 (button 7)    -> salir")
print()

ser = serial.Serial(PORT, BAUD, timeout=0.01)
time.sleep(2.0)
ser.reset_input_buffer()

targets = {k: float(v) for k, v in HOME.items()}
last_sent = {k: None for k in HOME.keys()}
last_buttons = {}
manual_enabled = True

last_loop = time.time()
last_send = 0.0

def force_sync_targets():
    global last_send
    for sid in targets:
        last_sent[sid] = None
    last_send = 0.0

force_sync_targets()
print("Control iniciado. Usa el joystick.\n")

try:
    while True:
        pygame.event.pump()
        now = time.time()
        dt = now - last_loop
        last_loop = now

        for line in read_serial_lines(ser):
            print("ESP32:", line)
            if "saludo iniciado" in line:
                manual_enabled = False
            elif "saludo terminado" in line:
                manual_enabled = True
                targets = {k: float(v) for k, v in HOME.items()}
                force_sync_targets()
            elif "coreografia detenida" in line:
                manual_enabled = True
                targets = {k: float(v) for k, v in HOME.items()}
                force_sync_targets()

        ax0 = normalize_axis(js.get_axis(0), axis_centers[0]) if js.get_numaxes() > 0 else 0.0
        ax1 = normalize_axis(js.get_axis(1), axis_centers[1]) if js.get_numaxes() > 1 else 0.0

        hat_x, hat_y = (0, 0)
        if js.get_numhats() > 0:
            hat_x, hat_y = js.get_hat(0)

        b0 = js.get_button(0) if js.get_numbuttons() > 0 else 0
        b1 = js.get_button(1) if js.get_numbuttons() > 1 else 0
        b2 = js.get_button(2) if js.get_numbuttons() > 2 else 0
        b3 = js.get_button(3) if js.get_numbuttons() > 3 else 0
        b4 = js.get_button(4) if js.get_numbuttons() > 4 else 0
        b5 = js.get_button(5) if js.get_numbuttons() > 5 else 0
        b6 = js.get_button(6) if js.get_numbuttons() > 6 else 0
        b7 = js.get_button(7) if js.get_numbuttons() > 7 else 0

        if b4 and not last_buttons.get("b4", 0):
            send_cmd(ser, "home")
            targets = {k: float(v) for k, v in HOME.items()}
            manual_enabled = True
            force_sync_targets()

        if b5 and not last_buttons.get("b5", 0):
            send_cmd(ser, "saludo")
            manual_enabled = False

        if b6 and not last_buttons.get("b6", 0):
            send_cmd(ser, "stop")
            manual_enabled = True
            targets = {k: float(v) for k, v in HOME.items()}
            force_sync_targets()

        if b7 and not last_buttons.get("b7", 0):
            print("Saliendo por boton rapido 4.")
            break

        last_buttons["b4"] = b4
        last_buttons["b5"] = b5
        last_buttons["b6"] = b6
        last_buttons["b7"] = b7

        if manual_enabled:
            targets[1] += (-ax0) * BASE_RATE * dt
            targets[2] += (-ax1) * HOMBRO_RATE * dt

            if b2:
                targets[3] -= CODO_RATE * dt
            if b3:
                targets[3] += CODO_RATE * dt

            targets[4] += hat_x * MUNECA1_RATE * dt
            targets[5] += (-hat_y) * MUNECA2_RATE * dt

            if b0:
                targets[6] -= GARRA_RATE * dt
            if b1:
                targets[6] += GARRA_RATE * dt

            for sid in targets:
                lo, hi = LIMITS[sid]
                targets[sid] = clamp(targets[sid], lo, hi)

        if manual_enabled and (now - last_send >= SEND_INTERVAL):
            for sid in range(1, 7):
                angle = int(round(targets[sid]))
                if last_sent[sid] != angle:
                    send_cmd(ser, f"s {sid} {angle}")
                    last_sent[sid] = angle
            last_send = now

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nInterrumpido por teclado.")

finally:
    ser.close()
    pygame.quit()
    print("Puerto serial cerrado. Fin.")
