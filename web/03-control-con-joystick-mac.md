# Control con joystick desde macOS

## Arquitectura de control

El joystick USB no se conecta directo al ESP32.

El flujo actual es:

```text
Joystick USB -> MacBook -> script Python -> puerto serial -> ESP32 -> PCA9685 -> servos
```

## Entorno Python recomendado

Se creo un entorno virtual con Python 3.13 porque con Python 3.14 `pygame` dio problemas de compilacion en macOS.

### Crear entorno

```bash
mkdir -p ~/robot_arm
cd ~/robot_arm
$(brew --prefix python@3.13)/bin/python3.13 -m venv .venv313
source .venv313/bin/activate
python -m pip install --upgrade pip
python -m pip install pygame pyserial
```

## Puerto serial actual

```text
/dev/cu.usbserial-10
```

## Mapeo del joystick Genius Max Fighter F-23U

### Ejes y hat
- `axis 0` -> base
- `axis 1` -> hombro
- `hat izquierda/derecha` -> muneca1
- `hat arriba/abajo` -> muneca2

### Botones
- `button 0` -> cerrar garra
- `button 1` -> abrir garra
- `button 2` -> codo hacia arriba
- `button 3` -> codo hacia abajo
- `button 4` -> home
- `button 5` -> saludo
- `button 6` -> stop
- `button 7` -> salir del script

## Comportamiento del script

El script hace:

- calibracion automatica de centro al iniciar
- zona muerta para corregir drift
- actualizacion continua de objetivos
- envio por serial solo cuando cambia el angulo

## Importante

Antes de ejecutar el script Python:

- cerrar Arduino IDE o Monitor Serial
- dejar el joystick quieto durante la calibracion inicial

## Ejecucion

```bash
cd ~/robot_arm
source .venv313/bin/activate
python joystick_arm.py
```

## Diagnostico rapido

### Error: Resource busy
Significa que otro programa tiene abierto el puerto serial, casi siempre Arduino IDE.

### El joystick se mueve solo
Repetir calibracion sin tocarlo durante los primeros 2 segundos.

### Un eje esta invertido
Invertir el signo en el script Python.
