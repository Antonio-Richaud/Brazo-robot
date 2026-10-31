# Simulación segura de seis articulaciones en Jetson Nano 2GB

**Fecha:** 30 de octubre de 2026  
**Estado:** simulador aislado, **26/26 pruebas aprobadas** y demostración CLI `--demo` ejecutada con éxito en la Jetson Nano 2GB (Python 3.6.9), sin acceso al hardware de los servos.  
**Rama:** `feat/jetson-nano-physical-ai`.

## Objetivo

Preparar la futura capa de control de seis servos sin conexión entre el
simulador y el PCA9685. **Esta fase no habilita ningún motor físico**.

- Script: [jetson/arm_simulation.py](../jetson/arm_simulation.py)
- Tests: [jetson/tests/test_arm_simulation.py](../jetson/tests/test_arm_simulation.py)
- Diagnóstico y desactivación del chip real (separado):
  [jetson/pca9685_safe.py](../jetson/pca9685_safe.py)
- Contrato actual del backend moderno: [control-center/backend/config.py](../control-center/backend/config.py),
  [controller.py](../control-center/backend/controller.py) y
  [robot_state.py](../control-center/backend/robot_state.py).
- Pruebas físicas realizadas previamente:
  [08-jetson-pca9685-i2c-pruebas.md](08-jetson-pca9685-i2c-pruebas.md).

## 1. Separación estricta

`jetson/arm_simulation.py` solo importa `argparse`, `json`, `math`,
`time` y `collections` (biblioteca estándar). No importa I²C,
GPIO, serial ni el diagnóstico del PCA9685. No tiene API de
habilitación PWM ni conexiones con la fuente de servos.

El estado `SIM_ARMED` es una **habilitación ficticia de simulación en RAM**.
Jamás debe confundirse con una señal OE baja, un motor energizado ni un
controlador real armado. No existe opción CLI para armar hardware.

El script no modifica el backend React/WebSocket existente ni crea una
conexión con el gemelo digital. Esa integración queda para otra etapa.

## 2. Parámetros idénticos a los configurados en el Control Center

La Jetson usa Python 3.6 y no puede importar directamente
`control-center/backend/config.py`, que usa características modernas.
Por tanto, los siguientes datos están copiados como constantes del contrato
actual: si se cambia ese contrato, se deben actualizar y probar ambas tablas.

| ID | Nombre backend | Canal PCA | Home simulado | Límites de referencia | Velocidad simulada |
|---:|---|---:|---:|---|---:|
| 1 | base | 0 | 90° | 10–170° | 70°/s |
| 2 | hombro | 1 | 50° | 15–165° | 55°/s |
| 3 | codo | 2 | 165° | 15–165° | 70°/s |
| 4 | muneca1 | 3 | 10° | 10–170° | 90°/s |
| 5 | muneca2 | 4 | 170° | 10–170° | 90°/s |
| 6 | garra | 5 | 40° | 20–140° | 90°/s |

**Los Home son valores iniciales exclusivamente matemáticos:** no hay
encoders y no se sabe si coinciden con la posición física real del brazo.
Estos límites aún no se han calibrado de manera individual para MG995/SG90
montados en la Jetson.

## 3. Máquina de estados del simulador

~~~mermaid
stateDiagram-v2
    [*] --> DISARMED
    DISARMED --> SIM_ARMED: arm_simulation()
    SIM_ARMED --> DISARMED: disarm_simulation()
    SIM_ARMED --> FAULT: watchdog vencido / reloj hacia atrás
    FAULT --> DISARMED: reset_fault()
~~~

- **DISARMED** (inicio): no acepta órdenes de movimiento simulado.
- **SIM_ARMED**: admite objetivos de los seis ejes solo después de una
  activación simulada explícita, valida IDs, números finitos y límites.
- **FAULT**: detiene el cambio de posiciones simuladas, mantiene objetivo
  igual a posición actual y exige `reset_fault()` antes de volver a simular.

El simulador limita el cambio por articulación a la velocidad de su tabla,
multiplicada por hasta **0.1 segundos de paso**, para no acumular saltos
si una iteración se demora. Su watchdog predeterminado vence tras
**1 segundo sin heartbeat ni orden válida**, pero solo se comprueba
cuando se invoca `tick()`, `heartbeat()` o una orden.

**Advertencia:** esto no equivale a un watchdog independiente,
limitador de aceleración, enclavamiento eléctrico, medición física de ángulo
o paro de emergencia. Los tres últimos aspectos siguen pendientes para
cualquier integración física.

## 4. Primera prueba en la Jetson (sin hardware)

Mantener la fuente de servos **apagada**, y `OE` del PCA9685 conectado
a **3.3 V**. Desde SSH en la Jetson:

~~~bash
cd ~/robot-lab/Brazo-robot
git pull --ff-only origin feat/jetson-nano-physical-ai
python3 -m unittest discover -s jetson/tests -v
~~~

**Resultado comprobado en la Jetson Nano 2GB (30-10-2026):**

```text
Ran 26 tests in 0.013s

OK
```

Las 26 pruebas incluyen nueve del diagnóstico PCA9685 simulado y 17 nuevas de simulación. Todas pasaron en **Python 3.6.9**. Ninguna prueba escribe registros del dispositivo físico.

Demostración matemática opcional, también sin hardware:

~~~bash
python3 jetson/arm_simulation.py --demo
~~~

**Demostración verificada en la Jetson el 30-10-2026.** Se observó la trayectoria de la base de 90° a 125°, avanzando
a velocidad simulada de 70°/s con pasos de 0.1 s:

~~~text
=== SIMULACION: 0 ACCESO A HARDWARE ===
T=0.1s base=97.0 deg
T=0.2s base=104.0 deg
T=0.3s base=111.0 deg
T=0.4s base=118.0 deg
T=0.5s base=125.0 deg
SIMULACION TERMINADA: sin motores, sin I2C y sin GPIO
~~~

La salida real confirmó los cinco pasos indicados, el texto `SIMULACION TERMINADA: sin motores, sin I2C y sin GPIO`, `fault_reason: null`, `hardware_enabled: false`, `mode: simulation_only`, `measured: false` para las seis articulaciones, y `state: DISARMED` tanto al iniciar como al finalizar.

También imprime estados JSON completos inicial y final con
`hardware_enabled: false`, `measured: false` y el estado
`DISARMED` al finalizar. Se ejecuta usando un reloj falso
determinista: no espera ni controla servos.

## 5. Riesgos y próximos pasos

1. **[Completado]** Ejecutar 26/26 tests con Python 3.6 en la Jetson (0.013 s, `OK`).
2. **[Completado]** Validar `python3 jetson/arm_simulation.py --demo` en la Jetson (90°, 97°, 104°, 111°, 118°, 125° y `DISARMED` final).
3. Diseñar una interfaz de comandos y eventos reutilizable entre el
   backend moderno de Mac y el futuro servicio Jetson, sin conectar aún PWM.
4. Validar límites de aceleración, secuencias, autenticación y reacción
   a pérdida de comunicación en modo simulación.
5. Antes de siquiera alimentar un servo: revisar el cableado real,
   polaridades, VCC/V+, tierra común, tensión medida y un **corte físico
   dedicado de potencia para los servos**.
6. Planear un adaptador I²C real en un módulo distinto, desarmado por defecto,
   protegido por validaciones y sin arranque Home automático. No implementarlo
   ni probarlo con la fuente energizada hasta tener las garantías anteriores.

**En esta etapa no se debe bajar OE, encender V+ ni conectar motores
para observar esta simulación.**

## 6. Próximo paso: establecer la línea base del dashboard 3D en Mac

El backend existente (`control-center/backend/main.py`) admite `--mode simulation`, `--perception off` y `--no-joystick`, mientras el frontend React/Three.js usa WebSocket (`useRobotSocket.js`) para consumir el estado del backend (`robot_state.py`, puerto 8765). Este backend requiere una versión moderna de Python y **no debe instalarse sobre el Python 3.6 de JetPack**.

La demostración anterior es un proceso local y aislado en Jetson: todavía **no publica datos al WebSocket del dashboard**. Antes de conectar ambos componentes:

1. Comprobar en la **Mac** que el repositorio existe localmente, y las versiones de Python/Node/npm disponibles.
2. Ejecutar el dashboard existente en modo simulación en la Mac, sin hardware y sin joystick, para verificar el punto de partida.
3. Definir un contrato de telemetría **unidireccional, solo lectura** desde la simulación de Jetson hacia el backend moderno. No aceptar comandos remotos de movimiento ni abrir puertos sin control de acceso.
4. Integrar gradualmente y añadir pruebas de compatibilidad del estado (IDs, nombres, límites, `measured: false`), sin tocar la rutina física ni arrancar `Home`.

Se debe mantener **OE a 3.3 V, V+ de los servos desconectado y `main` intacta**. La simulación no es un movimiento físico ni valida calibración mecánica.

## 7. Preparación del dashboard en Mac (30-10-2026; pasos 9.18 a 9.30)

**Confirmado mediante salidas de terminal del usuario en la MacBook Air:**

- Python predeterminado 3.14.7, Python 3.12.13 disponible; Node.js 24.18.0 y npm 11.16.0.
- Repositorio Mac `~/Documents/GitHub/Brazo-robot`: rama `feat/jetson-nano-physical-ai` sincronizada, sin cambios locales previos.
- Backend moderno: entorno virtual `control-center/backend/.venv` creado con Python 3.12.13; instalados `pygame==2.6.1`, `pyserial==3.5` y `websockets==16.0`; `pip check` sin incompatibilidades.
- Pruebas del backend Mac: **7/7** aprobadas (`python -m unittest discover -s tests -v`).
- Servidor Mac iniciado explícitamente con `ROBOT_WS_HOST=127.0.0.1 python main.py --mode simulation --perception off --no-joystick`. Proceso Python escuchando en `127.0.0.1:8765`, prueba TCP con `nc` exitosa. **Aún no se ha verificado el handshake/intercambio WebSocket ni el dashboard visual**.
- Frontend: `npm ci` exitoso (208 paquetes), pero audit inicial encontró 17 vulnerabilidades (10 moderadas, 7 altas). Se hizo `npm audit fix --dry-run` antes de `npm audit fix` **sin `--force`**. npm actualizó 30 paquetes y agregó uno.
- Auditoría posterior: **0 vulnerabilidades en dependencias de producción** (`npm audit --omit=dev`) y **6 moderadas en desarrollo** vinculadas con `minimatch`/ESLint, reportadas sin fix automático. npm advierte que ESLint 9.39.5 ya no tiene soporte; su revisión queda pendiente, sin forzar cambios.
- Validación frontend: `npm run lint` OK, `npm run build` OK (Vite 8.3.5, 571 módulos, 903 ms), `git diff --check` OK.
- Cambios confirmados y publicados en GitHub: commit **`999367e`** (`control-center/frontend/package-lock.json` únicamente), rama Jetson; `main` sin modificar. Cualquier commit de documentación posterior exige `git pull --ff-only` en Mac antes de continuar.

**Paso 9.31 confirmado por el usuario:** después de levantar Vite en la Mac, `http://127.0.0.1:5173/` **abre correctamente y el dashboard se visualiza bien**. Esta validación es visual; la interfaz React aún no se ha probado con órdenes de movimiento ni se ha comprobado su estado de conexión desde el navegador.

**Paso 9.32 confirmado en la Mac (30-10-2026):** el cliente WebSocket Python 3.12 (`websockets.connect("ws://127.0.0.1:8765")`) recibió exitosamente el snapshot JSON del backend, **sin enviar comandos**. Datos comunicados por el usuario: `protocol_version: 2`, `runtime_mode: simulation`, `mode: manual`, `connected: False`, seis articulaciones con `measured: False`:

| Eje | current | target |
|---|---:|---:|
| base | 90 | 90 |
| hombro | 50 | 50 |
| codo | 165 | 165 |
| muneca1 | 10 | 10 |
| muneca2 | 170 | 170 |
| garra | 40 | 40 |

Salida final: `VERIFICACION EXITOSA: simulacion y seis ejes`. Esto demuestra **handshake WebSocket y lectura de datos reales del backend**, no demuestra aún que la UI mueva el gemelo digital ni que haya conexión entre Jetson y Mac. **Paso 9.33, comprobación visual parcial:** el usuario compartió captura del navegador con estado **`CONNECTED`** en ENLACE LOCAL, `runtime_mode: simulation`, ESP32 **sin enlace**, joystick **ausente**, percepción **off**, escena 3D correctamente dibujada y seis tarjetas de articulación visibles en sus posiciones iniciales (Base `90°` y objetivo `90°`). Esto corrobora que la interfaz está consumiendo estado simulado del backend. **Paso 9.33 completado por confirmación del usuario:** después de ajustar Base de 90° hacia 105° en el dashboard, el usuario confirmó «Sí funciona» al ensayo de objetivo, lectura y movimiento visual del modelo 3D. Se considera validado el recorrido dashboard → WebSocket → backend en simulación → gemelo 3D para el eje Base. No se recibió una segunda captura ni medición física; la confirmación es del usuario. Siguiente ensayo seguro: coreografía `Saludo` exclusivamente en simulación, con retorno a Home. Mantener potencia de servos apagada y OE alto.

Esta preparación del dashboard es **independiente** del simulador Python 3.6 de la Jetson; todavía **no existe puente Jetson → Mac**. Mantener **OE alto a 3.3 V, V+ de servos apagado y ninguna habilitación física**.


## 8. Validación visual de coreografía Saludo en Mac (paso 9.34)

Después de confirmar que el control de Base funciona en el gemelo 3D, se solicitó al usuario presionar **Saludo** exclusivamente en la interfaz de la Mac con `runtime_mode=simulation` y WebSocket local. El usuario informó: **«Sí parece que funciona bien»**.

**Resultado:** la coreografía se considera **satisfactoria a nivel visual por observación del usuario**. No se recibieron trazas de cada articulación ni un snapshot posterior al final de la secuencia, por lo que **todavía no se ha comprobado programáticamente** el retorno exacto de los seis ejes a Home ni el restablecimiento de `mode=manual`. Esa es la siguiente verificación segura: recibir un snapshot WebSocket local **de solo lectura**, comprobar `runtime_mode=simulation`, `mode=manual` y `current=target=Home` para los seis servos (90, 50, 165, 10, 170, 40 grados respectivamente).

El servidor WebSocket de la Mac está aislado en `127.0.0.1:8765`. **Esta coreografía NO ejecutó el simulador Python 3.6 de la Jetson** ni validó salidas PCA9685. Mantener `OE` alto a 3.3 V y alimentación externa de servos apagada. La conexión Jetson→Mac y su contrato de telemetría de solo lectura siguen pendientes.

## 9. Paso 9.35: retorno Home verificado tras Saludo (Mac, 30-10-2026)

El usuario ejecutó en la Mac un **cliente WebSocket de solo lectura** después de probar `Saludo` en el dashboard. La salida recibida confirmó:

| Dato | Resultado |
|---|---|
| `runtime_mode` | `simulation` |
| `mode` | `manual` |
| Base | `current = target = 90` |
| Hombro | `current = target = 50` |
| Codo | `current = target = 165` |
| Muñeca vertical | `current = target = 10` |
| Giro de muñeca | `current = target = 170` |
| Garra | `current = target = 40` |

Resultado literal: `RESULTADO: HOME VERIFICADO`. **Seis de seis ejes correctos, sin medición física ni control PCA9685.** Con ello se cierra la línea base local del Control Center en Mac: WebSocket real, controles visuales, movimiento simulado de Base, coreografía Saludo visual y retorno virtual exacto a Home.

**Paso 9.36 propuesto:** validar acceso Mac→Jetson mediante el SSH existente y emitir un snapshot JSON desde `ArmSimulation().snapshot()` **sin abrir puertos en la Jetson ni generar salidas PWM**. A continuación se podrá definir un contrato versionado de telemetría de solo lectura y un adaptador en Mac con controles deshabilitados para datos remotos. Hasta que se pruebe, no afirmar que Jetson y Mac ya están enlazadas por telemetría.

## 10. Paso 9.36: SSH y preparacion del emisor JSONL

**Paso 9.36 confirmado el 30-10-2026:** la Mac leyo mediante SSH el JSON de `ArmSimulation().snapshot()` en la Jetson Nano 2GB, con Python 3.6.9, seis articulaciones, `state=DISARMED`, `hardware_enabled=false`, `measured=false` y salida final `JETSON_SIMULATION_READONLY_OK`. No se habilito ningun motor ni puerto adicional.

El cliente SSH emitio una advertencia por ausencia de intercambio de claves poscuantico en el servidor antiguo, pero la sesion se establecio correctamente. No modificar JetPack ni el servidor SSH sin revision previa.

**Paso 9.37 preparado en GitHub, aun NO probado en Jetson:**

- `jetson/telemetry_stream.py` es un emisor Python 3.6 de **13 tramas JSONL** exclusivamente por stdout, al ejecutar `--demo` de forma explicita. Simula en RAM la Base 90->125->90 grados, parte de `DISARMED` y termina en `DISARMED`. No lee stdin, no abre red ni accede a I2C, GPIO, serial o PWM.
- `jetson/tests/test_telemetry_stream.py` agrega **10 pruebas unitarias** a las 26 existentes. No afirmar que son 36/36 satisfactorias hasta obtener la salida de la Jetson.
- Cada trama publica `schema=brazo.jetson.sim.telemetry`, `schema_version=1`, `source=jetson_simulation`, `sequence`, `state`, `mode=simulation_only`, `fault_reason`, `hardware_enabled=false` y `servos` con seis articulaciones no medidas fisicamente.
- El estado `SIM_ARMED` dentro de esas tramas es un estado exclusivamente matematico; no habilita la señal OE ni ningun servo.

**Pendiente:** sincronizar y ejecutar las pruebas y el flujo JSONL en la Jetson. Todavia no existe puente entre esta fuente Jetson y el backend/WebSocket/React en Mac. El siguiente desarrollo debe validar esquemas y separar el modo monitor remoto de los controles de movimiento.

Conservar OE alto a 3.3 V, potencia externa de servos apagada y `main` intacta.
