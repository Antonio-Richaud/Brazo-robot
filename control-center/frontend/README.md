# Arm Control Center

Interfaz React + Three.js para visualizar el estado estimado del brazo, enviar
comandos manuales y representar nubes de puntos producidas por el backend.

```bash
npm ci
npm run dev
```

Por defecto se conecta a `ws://<host>:8765`. Para usar otra direccion:

```bash
VITE_ROBOT_WS_URL=ws://192.168.1.20:8765 npm run dev
```

Comprobaciones:

```bash
npm run lint
npm run build
```
