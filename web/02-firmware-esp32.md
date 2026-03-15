# Firmware ESP32

## Objetivo

El firmware del ESP32 hace estas tareas:

- Controla el PCA9685 por I2C.
- Recibe comandos por puerto serial.
- Mantiene posiciones objetivo por servo.
- Aplica movimiento suave.
- Ejecuta una coreografia llamada `saludo`.

## Comandos seriales disponibles

### Ayuda y diagnostico
- `help` -> muestra ayuda
- `status` -> muestra estado actual de servos

### Movimiento general
- `home` -> mueve todos los servos a home
- `s <id> <angulo>` -> mueve un servo a un angulo absoluto
- `d <id> <delta>` -> mueve un servo relativo a su posicion objetivo actual

### Configuracion
- `homev <id> <angulo>` -> cambia el home del servo
- `range <id> <min> <max>` -> cambia limites del servo

### Coreografia
- `saludo` -> ejecuta saludo fluido
- `stop` -> detiene la coreografia y regresa a home

## Home actual

```text
base    = 90
hombro  = 50
codo    = 165
muneca1 = 10
muneca2 = 170
garra   = 40
```

## Limites actuales

```text
base    10..170
hombro  15..165
codo    15..165
muneca1 10..170
muneca2 10..170
garra   20..140
```

## Movimiento suave

El firmware usa:

- velocidad maxima por servo
- aceleracion maxima por servo
- interpolacion suave para la coreografia

Esto evita movimientos bruscos y hace que el brazo se vea mas natural.

## Saludo actual

La coreografia `saludo` hace esto:

1. Parte de `home`.
2. Llega de forma fluida a una pose de saludo definida.
3. Mantiene una pausa corta.
4. Regresa suavemente a `home`.

La pose actual de saludo es:

```text
base    = 90
hombro  = 60
codo    = 90
muneca1 = 90
muneca2 = 100
garra   = 40
```

## Librerias necesarias en Arduino IDE

- `Wire.h`
- `Adafruit_PWMServoDriver.h`

## Notas operativas

- El Monitor Serial debe estar a 115200 baudios.
- Si el puerto esta ocupado, el script Python no podra abrirlo.
- El PCA9685 usa canales reales desde `0`, no desde `1`.
