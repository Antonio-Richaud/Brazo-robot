SERIAL_PORT = "/dev/cu.usbserial-10"
SERIAL_BAUD = 115200

CALIBRATION_SECONDS = 2.0
DEADZONE = 0.08

STATUS_POLL_INTERVAL = 2.0
SEND_INTERVAL = 0.06
LOOP_SLEEP = 0.01

# Velocidades en grados por segundo
BASE_RATE = 70.0
HOMBRO_RATE = 55.0
CODO_RATE = 70.0
MUNECA1_RATE = 90.0
MUNECA2_RATE = 90.0
GARRA_RATE = 90.0

HOME = {
    1: 90,   # base
    2: 50,   # hombro
    3: 165,  # codo
    4: 10,   # muneca1
    5: 170,  # muneca2
    6: 40    # garra
}

LIMITS = {
    1: (10, 170),
    2: (15, 165),
    3: (15, 165),
    4: (10, 170),
    5: (10, 170),
    6: (20, 140)
}

SERVO_NAMES = {
    1: "base",
    2: "hombro",
    3: "codo",
    4: "muneca1",
    5: "muneca2",
    6: "garra",
}
