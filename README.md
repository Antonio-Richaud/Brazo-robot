# Robot-IA

Robot brazo controlado con ESP32 + PCA9685 + servos MG995/SG90, con control manual por joystick USB desde macOS y una coreografia de saludo activable por serial.

## Estado actual del proyecto

Hasta este punto, el proyecto ya incluye:

- Control de 6 servos con ESP32 y PCA9685.
- Fuente dedicada de 5V / 10A para servos.
- Control suave por objetivos angulares.
- Comando `home` con posicion real calibrada.
- Comando `saludo` con movimiento fluido y retorno automatico a `home`.
- Control por joystick USB conectado a MacBook.
- Script en Python para traducir joystick -> serial -> ESP32.

## Hardware actual

### Servos
- Base giratoria: MG995
- Hombro: MG995
- Codo: MG995
- Muneca eje 1: SG90
- Muneca eje 2: SG90
- Garra: SG90

### Control
- ESP32
- PCA9685
- Fuente externa de 5V / 10A para servos
- MacBook como host del joystick USB
- Joystick Genius Max Fighter F-23U

## Mapeo actual del brazo

| ID | Articulacion | Canal PCA9685 |
|----|--------------|---------------|
| 1  | Base         | 0             |
| 2  | Hombro       | 1             |
| 3  | Codo         | 2             |
| 4  | Muneca1      | 3             |
| 5  | Muneca2      | 4             |
| 6  | Garra        | 5             |

## Home actual

```text
1) base    = 90
2) hombro  = 50
3) codo    = 165
4) muneca1 = 10
5) muneca2 = 170
6) garra   = 40
```

## Estructura recomendada del repositorio

```text
Robot-IA/
├── README.md
├── docs/
│   ├── 01-hardware-y-conexiones.md
│   ├── 02-firmware-esp32.md
│   └── 03-control-con-joystick-mac.md
├── firmware/
│   └── robot_arm_controller/
│       └── robot_arm_controller.ino
├── tools/
│   └── joystick_arm.py
└── web/
```

## Documentacion incluida

- `docs/01-hardware-y-conexiones.md`
- `docs/02-firmware-esp32.md`
- `docs/03-control-con-joystick-mac.md`
- `firmware/robot_arm_controller/robot_arm_controller.ino`
- `tools/joystick_arm.py`

## Siguientes pasos sugeridos

1. Guardar esta base en GitHub.
2. Agregar fotos reales del robot y del cableado.
3. Documentar limites mecanicos finos por articulacion.
4. Crear una segunda coreografia.
5. Pasar de control manual a secuencias grabadas.
6. En una fase posterior: vision artificial y autonomia.

## Comandos utiles de Git

```bash
git clone https://github.com/Antonio-Richaud/Robot-IA.git
cd Robot-IA

mkdir -p docs firmware/robot_arm_controller tools
# Copiar aqui los archivos de este paquete

git add .
git commit -m "docs: agrega documentacion inicial del brazo robot y control con joystick"
git push origin main
```
