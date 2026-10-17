# Raspberry Pi 4: control directo sin ESP32

Esta variante reemplaza ESP32 por Raspberry Pi 4 y conserva el PCA9685 y los
seis servos. El frontend React/Three.js, joystick USB, coreografias, simulacion
y percepcion continúan en la misma arquitectura.

## Conexiones Raspberry Pi 4 -> PCA9685

| Raspberry Pi 4 (BCM / pin fisico) | PCA9685 |
|---|---|
| GPIO2 / pin 3 (SDA1) | SDA |
| GPIO3 / pin 5 (SCL1) | SCL |
| 3.3 V / pin 1 | VCC (logica) |
| GND / pin 6 | GND |

- Direccion predeterminada del PCA9685: **0x40**, bus **I2C-1**.
- Los seis servos siguen en los canales 0 a 5, con los Home y limites
  originales documentados en `01-hardware-y-conexiones.md`.
- **V+** de servos se alimenta con fuente **externa estabilizada 5 V / 10 A**
  (revisar margen bajo carga y corriente de bloqueo); nunca con el pin 5 V
  de la Pi ni con su pin 3.3 V. Unir las tierras.
- Conectar un corte fisico de emergencia a la fuente de servos. Desarmar PWM
  NO corta la corriente; un servo puede perder par o reaccionar bruscamente.
- Verificar proteccion frente a caidas de voltaje, cables y corriente real.

## Instalacion en Raspberry Pi OS de 64 bits

Instala Raspberry Pi OS Bookworm o compatible. Se recomienda una Raspberry Pi
4 con 4 GB o mas si se desea ejecutar el frontend completo en el mismo equipo.

```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip i2c-tools python3-dev
sudo raspi-config
```

En Interfaces, habilitar I2C y reiniciar. Inspeccionar la direccion:

```bash
ls -l /dev/i2c-1
sudo i2cdetect -y 1
```

Debe aparecer `40` si el PCA9685 tiene direccion predeterminada. Si no
aparece, NO energizar los servos: revisar SDA, SCL, 3.3 V y GND.

```bash
git clone https://github.com/Antonio-Richaud/Brazo-robot.git
cd Brazo-robot/control-center/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-raspberry-pi.txt
```

En una red local confiable, para permitir el panel desde otra computadora:

```bash
ROBOT_WS_HOST=0.0.0.0 python main.py --mode raspberry-pi --perception off
```

No se necesita puerto USB serial ni firmware Arduino. El controlador permanece
**desarmado** tras el arranque. La UI se puede abrir desde otra computadora
usando la IP de la Pi en el puerto WebSocket 8765 y servir el frontend desde
Vite u otro servidor web. El servidor WebSocket **no tiene autenticacion**:
no exponerlo a Internet; segmentar la red o utilizar VPN.

Para el frontend (Node compatible con el package.json actual):

```bash
cd ../frontend
npm ci
npm run dev -- --host 0.0.0.0
```

Abrir `http://IP_DE_LA_PI:5173` desde una computadora de la misma LAN.

## Procedimiento de armado seguro

1. Mantener cortada la potencia externa de servos y verificar el PCA por I2C.
2. Desconectar o desacoplar mecanicamente si fuera necesario; ubicar
   **fisicamente** cada eje en su Home conocido: 90, 50, 165, 10, 170, 40.
   La Raspberry **no puede medir** esa posicion con los MG995/SG90.
3. Despejar la trayectoria, verificar topes mecanicos y probar sin carga.
4. Preparar un corte fisico de potencia accesible y alimentar la fuente externa.
5. Iniciar el backend. Verificar `PCA9685 conectado` y `PWM desarmado`.
6. Pulsar **Armar PWM**: en ese instante se escriben todos los pulsos Home.
   Si el brazo no esta fisicamente en Home, puede moverse inesperadamente.
7. Probar articulaciones una a una, con movimientos pequenos.
8. Solo despues ejecutar Saludo y Rutina.

**Cancelar / Home ordena movimiento.** `Desarmar PWM` libera el control, pero
no sustituye el corte electrico. En casos de riesgo, actuar sobre el corte
fisico externo. No habilitar autonomia ni colisiones desde RealSense sin
calibracion camara-base, medicion y barreras independientes.

## Validacion previa sin hardware

```bash
cd control-center/backend
python -m unittest discover -s tests -v
python -m compileall -q .
python main.py --mode simulation --perception simulated --no-joystick
```

Los tests Raspberry Pi utilizan un PCA9685 falso; no mueven servos ni sustituyen
la prueba en banco. Para pruebas de instalacion con I2C real, ejecutar primero
sin alimentacion externa y verificar que la UI indique desarmado.

## Compatibilidad

- `--mode hardware` conserva la ruta serial legacy al ESP32.
- `--mode raspberry-pi` controla directamente el PCA9685.
- `--mode simulation` no requiere hardware.
- `--perception off|simulated|realsense|remote` no cambia.
- `homev` / `range` en la interfaz de transporte, igual que firmware previo,
  se almacenan en RAM y no persisten reinicios.
- Frecuencia PWM: 50 Hz. Pulsos 500-2500 us heredados del firmware y
  **pendientes de calibracion** individual por modelo y montaje.
