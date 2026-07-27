# Manual de uso y pruebas

Este manual describe el flujo recomendado para probar el Control Center sin hardware y, posteriormente, con el brazo físico.

## 1. Requisitos

- Python 3.12 o 3.13.
- Node.js 20.19 o superior.
- npm.
- Para hardware: ESP32 con el firmware cargado, PCA9685, fuente independiente para servos y tierras comunes.
- Opcional: joystick Genius Max Fighter F-23U.
- Opcional: Intel RealSense D435i.

## 2. Preparar el backend

```bash
cd control-center/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Para RealSense instalada en el mismo equipo:

```bash
python -m pip install -r requirements-realsense.txt
```

## 3. Preparar el frontend

En otra terminal:

```bash
cd control-center/frontend
npm ci
```

## 4. Prueba segura sin hardware

Inicia el backend en simulación:

```bash
cd control-center/backend
source .venv/bin/activate
python main.py --mode simulation --perception simulated --no-joystick
```

Inicia el frontend:

```bash
cd control-center/frontend
npm run dev
```

Abre la dirección mostrada por Vite, normalmente `http://localhost:5173`.

Comprueba:

1. El WebSocket cambia a `connected`.
2. Los seis sliders actualizan el gemelo digital.
3. `Home`, `Saludo` y `Rutina` reproducen movimientos completos.
4. Al terminar una coreografía, el modo vuelve a `manual`.
5. Si reinicias el backend, el frontend intenta reconectarse automáticamente.
6. La percepción simulada muestra campo visual o nube de puntos sin controlar servos.

## 5. Pruebas automáticas

Backend:

```bash
cd control-center/backend
source .venv/bin/activate
python -m unittest discover -s tests -v
python -m compileall -q .
```

Frontend:

```bash
cd control-center/frontend
npm ci
npm run lint
npm run build
```

Todos los comandos deben terminar sin errores antes de integrar cambios en `main`.

## 6. Prueba con ESP32, sin energizar servos

Antes de conectar la fuente de los servos, valida únicamente la comunicación:

```bash
cd control-center/backend
source .venv/bin/activate
python main.py --mode hardware --perception off --no-joystick
```

El backend intenta detectar el puerto. Para indicarlo manualmente:

```bash
python main.py \
  --mode hardware \
  --perception off \
  --no-joystick \
  --serial-port /dev/cu.usbserial-10
```

Comprueba en la interfaz:

- Serial conectado.
- Puerto correcto.
- Seis servos presentes en telemetría.
- Home, límites y canales PCA correctos.

## 7. Prueba gradual con servos

1. Apaga la fuente de servos.
2. Coloca el brazo en una posición mecánicamente segura.
3. Verifica GND común entre fuente, PCA9685 y ESP32.
4. Energiza la fuente sin carga en la garra.
5. Mueve un solo servo con pasos pequeños desde el slider.
6. Repite con cada articulación.
7. Ejecuta `Home`.
8. Ejecuta `Saludo` y después `Rutina` solamente cuando los movimientos individuales sean seguros.

`Cancelar / Home` interrumpe una coreografía y ordena volver a Home. No sustituye un paro físico de emergencia.

## 8. Joystick

Ejecuta el backend sin `--no-joystick` y deja el control inmóvil durante la calibración inicial:

```bash
python main.py --mode hardware --perception off
```

Mapeo principal:

| Entrada | Acción |
|---|---|
| Axis 0 | Base |
| Axis 1 | Hombro |
| Button 2 / 3 | Codo |
| Hat | Muñecas |
| Button 0 / 1 | Cerrar / abrir garra |
| Button 4 | Home |
| Button 5 | Saludo |
| Button 6 | Cancelar y volver a Home |
| Button 7 | Rutina |

## 9. RealSense

Primero prueba la cámara como fuente de visualización, nunca como control autónomo:

```bash
python main.py --mode simulation --perception realsense --no-joystick
```

Para percepción remota desde Jetson, consulta `docs/04-realsense-jetson.md`.

No autorices movimientos a partir de profundidad hasta completar la calibración extrínseca entre la cámara y `robot_base`.

## 10. Problemas comunes

### No aparece el ESP32

```bash
ls /dev/cu.*
```

Cierra el Monitor Serial y cualquier programa que esté usando el mismo puerto.

### No aparece el joystick

Comprueba que macOS lo detecte y reinicia el backend. El sistema puede utilizarse sin joystick mediante `--no-joystick`.

### El frontend no conecta

- Verifica que el backend esté activo en el puerto `8765`.
- Revisa `VITE_ROBOT_WS_URL` si frontend y backend se ejecutan en equipos diferentes.
- Para aceptar conexiones remotas, configura `ROBOT_WS_HOST=0.0.0.0` únicamente en una red confiable.

### La compilación del frontend falla

```bash
node --version
rm -rf node_modules
npm ci
npm run build
```

### El brazo intenta golpear un límite

Corta la potencia de los servos. No amplíes rangos hasta revisar montaje, orientación del horn y posición Home.

## 11. Cierre correcto

Detén backend y frontend con `Ctrl+C`. Después apaga la fuente de los servos antes de desconectar señales o mover mecánicamente el brazo.
