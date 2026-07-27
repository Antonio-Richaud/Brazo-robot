# Firmware ESP32

El firmware controla el PCA9685, mantiene un modelo interno de posicion y
acepta comandos seriales a 115200 baudios.

## Comandos

| Comando | Funcion |
|---|---|
| `help` | Muestra ayuda |
| `status` | Devuelve estado interno de los seis ejes |
| `home` | Establece Home como objetivo |
| `s <id> <angulo>` | Objetivo absoluto |
| `d <id> <delta>` | Movimiento relativo |
| `homev <id> <angulo>` | Cambia Home en RAM |
| `range <id> <min> <max>` | Cambia limites en RAM |
| `saludo` | Ejecuta la secuencia de saludo |
| `rutina` | Ejecuta la secuencia de siete poses |
| `stop` | Cancela la coreografia y regresa a Home |

Los cambios hechos con `homev` y `range` no persisten despues de reiniciar el
ESP32.

## Movimiento

El control manual limita velocidad y aceleracion. Las coreografias utilizan
`smootherstep`, por lo que inician y terminan sin cambios bruscos de velocidad.
La maquina de estados no bloquea el `loop()` y permite recibir `status`, `help`
y `stop` durante una secuencia.

El delta de tiempo del integrador esta limitado a 50 ms y se reinicia al iniciar,
cancelar o terminar una coreografia. Esto evita un salto de posicion despues de
haber pasado varios segundos fuera del control manual. Los comandos seriales se
limitan a 64 caracteres para impedir crecimiento indefinido del buffer.

## Limitacion de la telemetria

`current` representa el angulo calculado por firmware, no la posicion medida en
el eje. Los MG995 y SG90 usados actualmente no devuelven encoder al ESP32.

## Riesgo de arranque

En `setup()` se escriben inmediatamente los valores Home. Si el brazo fue
apagado lejos de Home, puede moverse con fuerza al energizar. La siguiente fase
de seguridad debe añadir armado explicito o una secuencia de arranque controlada.
