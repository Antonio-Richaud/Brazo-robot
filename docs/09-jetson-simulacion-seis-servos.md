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

**Paso 9.37 ejecutado y comprobado en la Jetson real (30-10-2026):**

- `jetson/telemetry_stream.py` es un emisor Python 3.6 de **13 tramas JSONL** exclusivamente por stdout, al ejecutar `--demo` de forma explicita. Simula en RAM la Base 90->125->90 grados, parte de `DISARMED` y termina en `DISARMED`. No lee stdin, no abre red ni accede a I2C, GPIO, serial o PWM.
- `jetson/tests/test_telemetry_stream.py` agrega **10 pruebas unitarias** a las 26 existentes. **La Jetson aprobó las 36/36 pruebas en 0.064 s**, según salida real de terminal.
- Cada trama publica `schema=brazo.jetson.sim.telemetry`, `schema_version=1`, `source=jetson_simulation`, `sequence`, `state`, `mode=simulation_only`, `fault_reason`, `hardware_enabled=false` y `servos` con seis articulaciones no medidas fisicamente.
- El estado `SIM_ARMED` dentro de esas tramas es un estado exclusivamente matematico; no habilita la señal OE ni ningun servo.

**Validación real:** la Jetson actualizó su rama por `git pull --ff-only` hasta `2aac693`, ejecutó 36 pruebas con resultado `OK`, emitió **13 tramas JSONL** y superó la prueba de stdout: `Tramas recibidas: 13`, `Base inicial: 90.0`, `Base maxima: 125.0`, `Base final: 90.0`, `JETSON_TELEMETRY_JSONL_OK`. Todavía no existe puente hacia el backend/WebSocket/React en Mac.

Conservar OE alto a 3.3 V, potencia externa de servos apagada y `main` intacta.

## 11. Paso 9.38: receptor pasivo de telemetria en la Mac (preparado para probar)

**Código incorporado en GitHub, sin ejecución real todavía:**

- [control-center/backend/jetson_telemetry_reader.py](../control-center/backend/jetson_telemetry_reader.py): validador pasivo Python 3.12 que solo consume JSONL desde `stdin` con `--stdin-demo`; **no invoca SSH**, no usa sockets/WebSocket/serial, no escribe estado del backend ni puede enviar comandos al brazo.
- [control-center/backend/tests/test_jetson_telemetry_reader.py](../control-center/backend/tests/test_jetson_telemetry_reader.py): **22 pruebas nuevas** de contrato y rechazo de datos maliciosos o corruptos, usando el emisor matematico existente con reloj simulado. **Total esperado de tests backend Mac: 29 (7 existentes + 22 nuevos), aun no verificado por ejecucion real.**
- Valida esquema y versión exactos, fuente autorizada, secuencia consecutiva `0..12`, modo matemático `simulation_only`, `hardware_enabled=false`, seis IDs/canales/límites conocidos, `measured=false`, ángulos finitos y dentro de límites, estado inicial/final `DISARMED`, trayectoria de Base y retorno a Home.
- **Criterio de fallo cerrado:** si el flujo SSH falla, el origen cambia, los datos exceden tamaño, hay tramas incompletas/adicionales o posiciones inválidas, el receptor termina con error sin publicar resultados como válidos.
- En la prueba prevista, el operador establecerá la sesión **SSH autenticada desde su Mac** y pasará stdout al validador mediante `|` con `set -o pipefail`. La autenticación puede pedir contraseña; las advertencias SSH van a stderr.
- **Importante:** un JSONL válido no es prueba de movimiento físico; tampoco se integra todavía al dashboard. El backend WebSocket actual continúa en `--mode simulation` y el frontend consume el estado simulado local, no la Jetson.

**Próximo test en Mac:** sincronizar rama; ejecutar `.venv/bin/python -m unittest discover -s tests -v` desde `control-center/backend`; después ejecutar el flujo remoto `ssh ... 'cd ... && python3 jetson/telemetry_stream.py --demo' | control-center/backend/.venv/bin/python control-center/backend/jetson_telemetry_reader.py --stdin-demo`, con `set -o pipefail`. Resultado esperado `MAC_JETSON_TELEMETRY_READONLY_OK`, sujeto a comprobación real.

No activar la fuente de los servos; conservar OE alto a 3.3 V y `main` intacta.

## 12. Paso 9.38 confirmado y modo replay 9.39

**Paso 9.38 confirmado por salida real de la Mac (30-10-2026):** la rama se sincronizó por `git pull --ff-only`; el backend Python 3.12 ejecutó **29/29 tests en 0.015 s, OK**. La Mac inició una sesión SSH autenticada con `antonio@jetson-nano.local`, recibió las 13 tramas JSONL del emisor Jetson y el receptor validó `source=jetson_simulation`, versión 1, trayectoria Base `90, 90, 97, 104, 111, 118, 125, 118, 111, 104, 97, 90, 90`, estado final `DISARMED`, `hardware_enabled=False`, `measured=False`. Salida de éxito: `MAC_JETSON_TELEMETRY_READONLY_OK`. La advertencia SSH sobre KEX poscuántico sigue siendo no bloqueante.

**Paso 9.39 implementado en rama, todavía pendiente de pruebas en Mac:**

- `control-center/backend/jetson_demo_monitor.py`: recibe **únicamente** las 13 tramas completas de demostración por `stdin`, validadas antes de abrir el WebSocket; posteriormente las **reproduce localmente** cada 0.1 s, con pausa de 1.5 s entre ciclos, para inspeccionar el gemelo 3D. **Esto es replay de una demostración simulada; NO telemetría en vivo ni posición física**.
- El monitor solamente escucha en `127.0.0.1:8767`; **no** crea `RobotController`, `SerialManager`, conexión SSH propia, servicios en Jetson ni rutas de control. Instancia WebSocket con `command_handler=None`, por lo que ignora comandos entrantes. Estado publicado: `runtime_mode=jetson_replay`, `mode=monitor`, ESP32 desconectado, seis articulaciones estimadas.
- `control-center/frontend/src/App.jsx`: reconoce el modo de replay, identifica la escena como **Reproducción Jetson · simulación**, deshabilita todos los controles de movimiento (Home, Saludo, Rutina, Cancelar/Home y deslizadores) y bloquea los envíos desde el componente. El WebSocket del monitor además carece de manejador de comandos.
- `control-center/backend/tests/test_jetson_demo_monitor.py`: se añadieron **10 pruebas** de aislamiento, bloqueo ante entrada inválida, trayectoria, estado monitor y ausencia de comandos. Total esperado de backend Mac: **39 tests (29 existentes + 10 nuevos)**, sin afirmar éxito hasta ejecución real.
- Mantener la interfaz local existente conectada a `127.0.0.1:8765` y el nuevo monitor separado a `127.0.0.1:8767`, sin modificar `main`.

**Paso 9.39 confirmado en la Mac el 30-10-2026:** tras actualizar la rama, la suite del backend ejecutó **39/39 tests OK en 0.030 s**; `npm run lint` completó sin errores y `npm run build` de Vite 8.3.5 compiló 571 módulos en **539 ms**. `git status -sb` mostró la rama sincronizada y limpia. Estas pruebas no significan que el servicio de monitor o la UI remota ya estén funcionando.

**Seguridad:** sigue apagada la fuente externa de servos; el pin OE del PCA9685 continúa a 3.3 V. El monitor no usa hardware Jetson/ESP32, solo posiciones matemáticas registradas.


## 13. Paso 9.40: arranque de monitor replay por SSH (pendiente)

**Prueba propuesta desde Mac**, con los dos servicios originales (backend local :8765 y frontend :5173) intactos. En terminal independiente:

```bash
cd ~/Documents/GitHub/Brazo-robot
git pull --ff-only origin feat/jetson-nano-physical-ai
set -o pipefail
ssh -T -o ConnectTimeout=10 antonio@jetson-nano.local \
  'cd "$HOME/robot-lab/Brazo-robot" && python3 jetson/telemetry_stream.py --demo' \
  | control-center/backend/.venv/bin/python \
      control-center/backend/jetson_demo_monitor.py --stdin-demo
```

**Resultado esperado, no verificado todavía:** `JETSON_REPLAY_MONITOR_READY ws://127.0.0.1:8767`. El monitor valida las 13 tramas completas antes de comenzar a reproducirlas de manera repetida, hasta detener el proceso con `Ctrl+C`. Si SSH falla o el JSONL resulta inválido, **no inicia** el servidor WebSocket del monitor.

Solo después del arranque confirmado se probará el frontend en puerto 5174, apuntando explícitamente a WebSocket 8767. Los datos se generaron por simulación en Jetson, no proceden de sensores ni actuadores; el WebSocket de reproducción tiene `command_handler=None` y el frontend deshabilita controles al detectar `jetson_replay` / `monitor`.

Mantener OE a 3.3 V, fuente externa de servos apagada, sistema JetPack sin actualizaciones arriesgadas y rama `main` intacta.

## 14. Paso 9.40 verificado y prueba visual 9.41 pendiente

**Confirmado por salida de terminal del usuario (30-10-2026):** la Mac inició una nueva sesión SSH autenticada, leyó las 13 tramas del emisor Python 3.6 de la Jetson y ejecutó el monitor separado `jetson_demo_monitor.py --stdin-demo`. El proceso informó:

```text
JETSON_REPLAY_MONITOR_READY ws://127.0.0.1:8767
Modo: replay Jetson matematico / solo lectura / sin motores. Detener con Ctrl+C.
```

El puerto 8767 pertenece exclusivamente al monitor de reproducción Mac en loopback, con `command_handler=None` y `mode=monitor`; se mantiene separado del backend local 8765. La advertencia SSH sobre KEX no poscuántico continúa siendo una limitación conocida del servidor antiguo, no un fallo de transporte.

**Aún no comprobado:** conexión desde React, animación 3D de la Base, bloqueo visual de los controles y UX del modo replay. Se propone iniciar una **segunda instancia de Vite en 5174**, con `VITE_ROBOT_WS_URL=ws://127.0.0.1:8767` únicamente en el comando de arranque (sin editar `.env` y sin alterar la instancia 5173). Verificar en navegador que `Runtime=jetson_replay`, `Modo=monitor`, `CONNECTED`, trayectoria visual 90→125→90 y controles deshabilitados.

No interpretar este replay de una demo finita como telemetría continua ni medición física. Mantener alimentación de servos apagada, OE alto a 3.3 V y rama `main` sin cambios.

## 15. Paso 9.41: dashboard replay 3D visible (desfase de angulo por verificar)

**Confirmación visual del usuario (30-10-2026):** el segundo dashboard en `http://127.0.0.1:5174/` **se ve bien y el brazo virtual está en movimiento repetido**. Esto confirma visualmente el camino Jetson (demo matemática) → SSH (13 JSONL) → monitor de replay Mac (WebSocket `127.0.0.1:8767`) → UI React/Three.js. El usuario describió el recorrido como **«90 a 180 a 90»**.

**Discrepancia abierta:** el código verificado establece Base `90→125→90` y el validador pasivo rechazó máximos inesperados en las pruebas. El límite configurado para Base es 170°, y el modelo 3D usa `degToRad(base.current - 90)`; por tanto el máximo esperado de la rotación **relativa** del modelo es 35°. Los **180° reportados por el usuario no se han corroborado en valores numéricos**. No etiquetar este resultado como recorrido de 180° ni modificar límites para acomodarlo.

**Siguiente verificación 9.42:** recibir estados WebSocket de `ws://127.0.0.1:8767` desde un cliente Mac **solo lectura** durante varios segundos; confirmar `runtime_mode=jetson_replay`, `mode=monitor`, rango Base `90..125°`, seis servos `measured=false` y fuente de datos simulada. Aclarar aparte que Home/Saludo/Rutina/Cancelar/sliders realmente aparecen deshabilitados; la confirmación visual genérica no acredita cada control.

El replay es de una demo almacenada de 13 tramas, no streaming de sensores ni una lectura física. Mantener el monitor abierto, OE alto a 3.3 V, servos sin alimentación externa y `main` sin modificaciones.

## 16. Paso 9.42: rango 90-125 confirmado por WebSocket (30-10-2026)

El usuario ejecutó en la Mac un cliente Python de **solo recepción** contra `ws://127.0.0.1:8767` durante siete segundos. Recibió **27 estados** del monitor y confirmó las aserciones de `runtime_mode=jetson_replay`, `mode=monitor`, seis articulaciones y `measured=false` en todos los ejes.

**Salida comprobada:**

```text
Lecturas recibidas: 27
Ángulos observados: [90.0, 97.0, 104.0, 111.0, 118.0, 125.0]
Mínimo: 90.0
Máximo: 125.0
Objetivos: [90.0, 125.0]
REPLAY_BASE_90_125_OK
```

La telemetría recibida demuestra que el ángulo de Base **no supera 125°** en esta reproducción. La descripción anterior del usuario «90 a 180 a 90» no corresponde a los datos publicados por el monitor; la causa visual exacta no está confirmada. `robotModel.js` utiliza una rotación relativa `base.current - 90`, por lo que la escena recibe hasta 35° de rotación relativa desde Home.

**Próxima comprobación 9.43:** verificar directamente en la UI en `http://127.0.0.1:5174/` que Home, Saludo, Rutina, Cancelar/Home y los seis deslizadores estén deshabilitados con `runtime_mode=jetson_replay` y `mode=monitor`. No dar por probada la protección de cada control por las pruebas previas de movimiento. No enviar órdenes remotas al hardware para comprobarlo.

Esta reproducción usa datos de un simulador matemático y no encoders, percepción ni servo físico. Mantener OE alto a 3.3 V, potencia externa apagada y rama `main` intacta.

## 17. Paso 9.43: verificacion DOM de controles bloqueados (30-10-2026)

El usuario compartió una captura de Chrome DevTools del dashboard `5174` que confirma cuatro botones de acción en estado `disabled=true`: **Home, Saludo, Rutina, Cancelar/Home**. La inspección de los controles de articulación mostró **`Deslizadores bloqueados: 6 de 6`** y la salida **`VERIFICACION: CONTROLES_BLOQUEADOS_OK`**.

La verificación visual/DOM, sumada a `command_handler=None` del WebSocket del monitor de replay, cierra la prueba de bloqueo de controles en el modo de **reproducción Jetson simulada**. No constituye una verificación de seguridad de servos físicos ni demuestra captura de telemetría en tiempo real.

La misma captura contiene repetidas advertencias de Three.js sobre `PCFSoftShadowMap` obsoleto y un contador de un error rojo, cuya descripción no es visible. Este aspecto se deja expresamente pendiente de diagnóstico de consola; no asumir que el mensaje `undefined` devuelto por el bloque de inspección es un error (es normal).

**Próximo paso:** identificar el error rojo en DevTools y revisar en una etapa separada el warning repetitivo de sombras sin romper la escena. Mantener `OE` alto, alimentación externa de servos apagada y rama `main` intacta.

## 18. Paso 9.44: limpieza de errores y advertencias del dashboard 3D (30-10-2026)

Tras cerrar la prueba de controles bloqueados, una captura de DevTools confirmó que el error rojo visible en `:5174` era **404 `/favicon.ico`**. Se observaban además numerosas advertencias repetidas de Three.js por usar la opción obsoleta `PCFSoftShadowMap`.

**Correcciones de código publicadas en la rama, aún sin verificar en navegador:** favicon vectorial en `control-center/frontend/public/favicon.svg`, referencia explícita en `control-center/frontend/index.html` y sombras del `<Canvas>` configuradas como `{ type: THREE.PCFShadowMap }` mediante una constante `SHADOW_SETTINGS` en `control-center/frontend/src/RobotScene.jsx`. La documentación oficial de Three.js recomienda `PCFShadowMap` para las versiones actuales. No se cambió el movimiento, el render geométrico del brazo, los controles ni el backend.

**Siguiente validación única:** actualizar la rama en Mac y ejecutar `npm run lint` + `npm run build`; recargar `http://127.0.0.1:5174/` y revisar en Chrome si el icono SVG responde con HTTP 200 y dejan de aparecer el 404 y las advertencias PCFSoftShadowMap. El dashboard debe seguir recibiendo `runtime_mode=jetson_replay` con controles bloqueados. No asumir éxito antes de la salida del usuario.

Las pruebas siguen siendo exclusivamente de software y replay matemático; no energizar motores ni modificar la rama `main`.

## 19. Paso 9.45: recompilación y favicon SVG verificados (30-10-2026)

La salida compartida por el usuario confirma que el checkout de Mac integró el cambio de favicon y sombras hasta commit `45cd2ff` por fast-forward. `npm run lint` terminó sin errores, `npm run build` produjo **571 módulos con Vite 8.3.5** en **539 ms**, y la petición `curl` a `http://127.0.0.1:5174/favicon.svg` devolvió **`FAVICON_HTTP_200`**.

El error original del favicon se ha corregido en la entrega del recurso SVG; **sigue pendiente verificar en la consola del navegador tras recarga limpia** que no se solicite `/favicon.ico` y no aparezca el aviso deprecado `THREE.WebGLShadowMap: PCFSoftShadowMap ...`. Una compilación correcta no prueba ausencia de advertencias runtime.

**Próxima prueba:** borrar la consola DevTools, recargar el segundo dashboard `5174` con el monitor en `8767`, observar varios segundos el movimiento 90°→125°→90° y los controles bloqueados, y comprobar ausencia de errores/advertencias nuevos. No se requieren más cambios de código antes de recibir esa evidencia.

Mantener `main` sin cambios, potencia de servomotores apagada y OE conectado a 3.3 V.

## 20. Paso 9.46: inspección visual de consola con filtro de errores

El usuario informó **«Ya está limpio»** y compartió captura del segundo dashboard (puerto 5174), con escena Three.js visible y enlace `CONNECTED` en modo `MONITOR`. La pestaña Console no presenta entradas rojas y el error previo de `/favicon.ico` ya no aparece; la petición al nuevo SVG había sido validada con `FAVICON_HTTP_200`.

**Precisión de la prueba:** el selector de Chrome está en **`Solo Errores`**, no en todos los niveles. El contador del navegador muestra **2 advertencias** y DevTools indica **5 mensajes ocultos**. Por ello, la desaparición de las advertencias recurrentes `PCFSoftShadowMap` **aún debe comprobarse** en consola sin filtro; no marcar el diagnóstico de warnings como concluido.

**Paso siguiente:** seleccionar `Niveles predeterminados` / todos los niveles, limpiar consola, recargar y observar las advertencias nuevas. Confirmar movimiento del gemelo y modo monitor sin alterar datos de Jetson ni servos. Mantener fuente física apagada y OE alto.

## 21. Paso 9.47: avisos residuales de WebSocket y Clock (30-10-2026)

Tras habilitar los niveles de consola, la captura del usuario en 5174 confirma que ya no se muestran ni el error de favicon ni advertencias por `PCFSoftShadowMap`; la interfaz continúa `CONNECTED` y en modo `MONITOR` con el gemelo 3D. Quedan dos advertencias:

- Un WebSocket a `ws://127.0.0.1:8767/` se cierra antes de completar el handshake. `main.jsx` usa React Strict Mode; el anterior efecto de `useRobotSocket.js` creaba el WebSocket sin demora y lo cerraba siempre en cleanup. En desarrollo Strict Mode ejecuta un ciclo extra de efectos, que puede generar ese warning.
- `THREE.Clock` ha quedado obsoleto desde Three.js r183. La advertencia aparece al crear `<Canvas>` y está relacionada con la implementación interna de React Three Fiber 9.x; no es una llamada propia a `new THREE.Clock` en `RobotScene.jsx`.

**Cambio publicado en la rama sin pruebas reales todavía:** `src/useRobotSocket.js` pospone el primer handshake por un tick, cancela temporizadores de reconexión al desmontar, gestiona estado de efecto individual y no cierra sockets en `CONNECTING` (espera hasta `onopen` para cerrar si la instancia se descartó). No se cambió `main.jsx`, la geometría 3D, bibliotecas ni el modo monitor de solo lectura.

**Próxima prueba:** `git pull --ff-only`, `npm run lint`, `npm run build` en Mac y Chrome DevTools (limpiar y recargar) para confirmar la corrección de WebSocket; el aviso `THREE.Clock` puede persistir hasta que `@react-three/fiber` migre a `THREE.Timer`. No degradar versiones ni mutear warnings sin necesidad. Esta nota no afirma que las advertencias ya estén eliminadas.

Mantener la separación de control físico y monitor, servos apagados, OE alto a 3.3 V, `main` sin cambios.
