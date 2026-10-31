# Simulación segura de seis articulaciones en Jetson Nano 2GB

**Fecha:** 30 de octubre de 2026  
**Estado:** código y 17 pruebas unitarias añadidos a GitHub; **pendiente ejecutar en Jetson Nano real con Python 3.6**.  
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

Se esperan **26 pruebas totales**: nueve antiguas del diagnóstico PCA9685
y 17 nuevas de simulación. Es necesario confirmar el resultado en
Python **3.6.9** antes de declararlas aprobadas. Ninguna prueba escribe
registros del dispositivo físico.

Demostración matemática opcional, también sin hardware:

~~~bash
python3 jetson/arm_simulation.py --demo
~~~

En la demostración, la base pasa en datos de 90° a 125°, avanzando
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

También imprime estados JSON completos inicial y final con
`hardware_enabled: false`, `measured: false` y el estado
`DISARMED` al finalizar. Se ejecuta usando un reloj falso
determinista: no espera ni controla servos.

## 5. Riesgos y próximos pasos

1. Ejecutar los 26 tests en Jetson y validar `--demo` (todavía pendientes).
2. Diseñar una interfaz de comandos y eventos reutilizable entre el
   backend moderno de Mac y el futuro servicio Jetson, sin conectar aún PWM.
3. Validar límites de aceleración, secuencias, autenticación y reacción
   a pérdida de comunicación en modo simulación.
4. Antes de siquiera alimentar un servo: revisar el cableado real,
   polaridades, VCC/V+, tierra común, tensión medida y un **corte físico
   dedicado de potencia para los servos**.
5. Planear un adaptador I²C real en un módulo distinto, desarmado por defecto,
   protegido por validaciones y sin arranque Home automático. No implementarlo
   ni probarlo con la fuente energizada hasta tener las garantías anteriores.

**En esta etapa no se debe bajar OE, encender V+ ni conectar motores
para observar esta simulación.**
