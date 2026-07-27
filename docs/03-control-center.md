# Control Center

## Flujo

```text
Joystick -> pygame -> RobotController -> serial -> ESP32
                                  |
                                  +-> RobotState -> WebSocket -> React/Three.js
```

El backend sigue disponible aunque no encuentre ESP32 o joystick. Esto permite
diagnosticar cada componente y desarrollar la interfaz en simulacion.

## Mapeo Genius Max Fighter F-23U

| Entrada | Accion |
|---|---|
| Axis 0 | Base |
| Axis 1 | Hombro |
| Button 2 | Codo hacia abajo |
| Button 3 | Codo hacia arriba |
| Hat izquierda/derecha | Muñeca vertical |
| Hat arriba/abajo | Giro de muñeca |
| Button 0 | Cerrar garra |
| Button 1 | Abrir garra |
| Button 4 | Home |
| Button 5 | Saludo |
| Button 6 | Cancelar y volver a Home |
| Button 7 | Rutina |

## Opciones del backend

```text
--mode hardware|simulation
--serial-port RUTA
--no-joystick
--perception off|simulated|realsense|remote
--realsense-serial SERIAL
--perception-url URL
```

Ejemplo completo de desarrollo:

```bash
python main.py --mode simulation --perception simulated --no-joystick
```

## Variables de entorno

| Variable | Uso |
|---|---|
| `ROBOT_SERIAL_PORT` | Puerto fijo del ESP32 |
| `ROBOT_WS_HOST` | Host del WebSocket; default `127.0.0.1` |
| `ROBOT_WS_PORT` | Puerto del Control Center; default `8765` |
| `REALSENSE_SERIAL` | Serie de la D435i |
| `REALSENSE_ENABLE_IMU` | `1` para solicitar accel/gyro |
| `REALSENSE_ENABLE_COLOR` | `1` para activar RGB; apagado en la nube inicial |
| `ROBOT_PERCEPTION_URL` | Nodo remoto de percepcion |
| `VITE_ROBOT_WS_URL` | WebSocket usado por el frontend |

## Mejoras de estabilidad incluidas

- El joystick se reactiva al terminar `saludo` o `rutina`.
- Los sliders reenvian solamente el servo modificado.
- El delta de tiempo del joystick se limita para evitar saltos despues de una
  pausa del proceso.
- Los ACK `OK` de movimiento no llenan la consola.
- El WebSocket reenvia estado solamente cuando cambia su revision.
- El frontend intenta reconectarse automaticamente.
