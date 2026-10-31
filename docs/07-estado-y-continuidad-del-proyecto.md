# Estado del proyecto y documento de continuidad — Brazo Robot + Jetson Nano

**Fecha de corte inicial:** 26 de octubre de 2026  
**Última actualización:** 30 de octubre de 2026 (Jetson 36/36 tests y JSONL verificados; Mac 39/39 tests, lint/build correctos, canal SSH validado; reproducción 3D de datos Jetson pendiente)
**Repositorio:** https://github.com/Antonio-Richaud/Brazo-robot  
**Rama de trabajo actual:** feat/jetson-nano-physical-ai  
**Punto de partida del código:** main, commit 8251aa902c04192c4e1d8ed143515d59bfdd7f7a  
**Bitácora de instalación:** [06-bitacora-instalacion-jetson-nano.md](06-bitacora-instalacion-jetson-nano.md)

> **Lectura recomendada al retomar tras perder el contexto:** este documento recoge el objetivo final, el estado confirmado, la arquitectura existente, las decisiones de diseño, las restricciones y el siguiente trabajo seguro. No asumir que una integración descrita en el código ya está instalada ni probada sobre el robot real.

## 1. Resumen de continuidad en un minuto

El objetivo es un **sandbox de IA/robótica física**: brazo de seis grados de libertad, control manual por joystick, gemelo digital 3D sincronizado, visión de profundidad con Intel RealSense D435i y, posteriormente, control por gestos y un agente que pueda planear acciones sujetas a límites de seguridad.

**Se hizo hasta ahora:**

- Se analizó el repositorio preexistente y su control por ESP32/PCA9685, backend Python y frontend React/Three.js.
- Se exploró una implementación de control directo para Raspberry Pi 4 en una rama/PR independiente; no está fusionada.
- Se eligió la **NVIDIA Jetson Nano 2GB original** como equipo del laboratorio.
- Se instaló JetPack 4.6.1 / Ubuntu 18.04.6 / L4T R32.7.1 y se habilitó el acceso de red por SSH.
- Se verificaron CUDA 10.2.300, cuDNN 8.2.1, TensorRT 8.2.1.8 y OpenCV 4.1.1.
- Se instaló pip/venv de Python 3.6 y se creó un entorno virtual independiente para usar las bibliotecas NVIDIA.
- Se clonó el repositorio y se seleccionó una rama nueva específica de Jetson.
- Se conectó el PCA9685 a la Jetson por J6 e I²C bus 1: dirección 0x40 detectada, MODE1/MODE2/PRE_SCALE validados, frecuencia nominal 50 Hz preparada y salidas FULL OFF confirmadas en canales 0 y 15. OE está conectado físicamente a 3.3 V según la comprobación de cableado comunicada por el usuario.
- Se agregó jetson/pca9685_safe.py (diagnóstico solo lectura y comando exclusivo FULL OFF, sin orden de armado/movimiento); `status` fue probado con el PCA9685 real y las **nueve pruebas simuladas se ejecutaron en la Jetson (9/9, OK, 0.003 s)**. El comando `disable-all` se ejecutó con éxito sobre el PCA9685 real (FULL OFF 16/16).
- Se añadió `jetson/arm_simulation.py` con estado `DISARMED`, `SIM_ARMED` solo matemático, validación de los seis ejes, velocidad máxima por eje y watchdog de simulación. Las 17 pruebas nuevas se ejecutaron en la Jetson junto con las nueve previas (**26/26 OK, 0.013 s**).
- **No** se ha instalado el runtime completo, conectado la D435i, energizado el brazo desde Jetson ni movido servos.

**Siguiente tarea:** ejecutar el **monitor pasivo `jetson_demo_monitor.py` en Mac**, alimentado con las 13 tramas JSONL validadas obtenidas por SSH desde Jetson. Las pruebas del monitor están confirmadas (39/39 backend Mac, ESLint y build OK), pero falta verificar que abra `127.0.0.1:8767`, reproduzca datos y que la UI en `5174` muestre el movimiento con controles bloqueados. El backend normal en `8765` sigue aislado. No hay streaming físico ni habilitación del PCA9685. Mantener `OE` alto, fuente de servos apagada y `main` intacta.

## 2. Objetivo y alcance funcional

El proyecto se concibe como una plataforma extensible con estas capacidades:

1. **Control manual:** joystick USB, comandos de movimiento individual y secuencias.
2. **Gemelo digital 3D:** representar el brazo en Three.js, mostrar movimiento y telemetría; distinguir posición estimada y medida.
3. **Percepción 3D:** capturar profundidad RealSense, crear nube reducida y detectar obstáculos; calibrar la cámara respecto a la base del robot antes de usar esa información para decisiones físicas.
4. **Autonomía asistida:** un agente propone acciones o trayectorias; una capa de control independiente valida límites, habilitación, estado y seguridad.
5. **Desarrollo seguro:** simulación primero, hardware después, interruptor físico de potencia para servos antes de movimientos autónomos.

La Jetson puede actuar inicialmente como nodo ligero de visión/servicios NVIDIA; la posibilidad de **reemplazar el ESP32 mediante control directo PCA9685 desde I2C de la Jetson** es una línea de trabajo planteada, no una función ya implementada.

## 3. Hardware del brazo y conexiones existentes

La arquitectura que **sí está documentada y programada en main** utiliza:

- ESP32 como controlador de los seis servos.
- Módulo PCA9685 como generador PWM.
- Fuente externa de servos de 5 V / 10 A.
- Servos MG995 y SG90.
- Joystick Genius Max Fighter F-23U.
- Cámara Intel RealSense D435i prevista para visión; número de serie 926522071007.
- Jetson Nano 2GB para procesamiento de percepción/IA y futura integración física.
- Mac como equipo de desarrollo y alojamiento inicial del dashboard/servidor moderno.

**Mapa de articulaciones registrado en config.py y en la documentación de hardware:**

| ID | Articulación | Modelo | Canal PCA9685 | Home | Límites |
|---:|---|---|---:|---:|---|
| 1 | Base | MG995 | 0 | 90° | 10–170° |
| 2 | Hombro | MG995 | 1 | 50° | 15–165° |
| 3 | Codo | MG995 | 2 | 165° | 15–165° |
| 4 | Muñeca vertical | SG90 | 3 | 10° | 10–170° |
| 5 | Giro de muñeca | SG90 | 4 | 170° | 10–170° |
| 6 | Garra | SG90 | 5 | 40° | 20–140° |

**Conexión documentada para el ESP32 actual:**

| Señal ESP32 | PCA9685 |
|---|---|
| 3.3 V | VCC lógico |
| GND | GND |
| GPIO 21 | SDA |
| GPIO 22 | SCL |

La potencia de 5 V para servos entra por la alimentación de potencia del PCA9685, separada de la lógica; las tierras deben tener referencia común. **No extrapolar estos pines a la Jetson:** su encabezado, bus I2C, niveles lógicos y alimentación deben verificarse por separado antes de cablear.

**Advertencia:** los ángulos Home y los topes son referencias programadas; no se han recalibrado para una nueva instalación. El firmware usa pulsos de 500 a 2500 microsegundos para todos los servos y requiere calibración individual antes de ampliar recorridos. No se dispone de sensores de posición/encoders: la posición reportada por el firmware es estimada.

Documentación de origen: [01-hardware-y-conexiones.md](01-hardware-y-conexiones.md).

## 4. Arquitectura que existe actualmente en el repositorio

~~~mermaid
flowchart LR
    J[Joystick USB] --> B[Backend Python en Mac]
    W[Control Center React y Three.js] <-->|WebSocket :8765| B
    B <-->|Serial 115200| E[ESP32]
    E --> P[PCA9685 y 6 servos]
    C[Intel RealSense D435i] --> N[Jetson Nano 2GB]
    N -. nube reducida WebSocket :8766 .-> B
~~~

**Significado del diagrama:** el trayecto del ESP32 tiene código en el repositorio; el trayecto Jetson/RealSense es una **arquitectura prevista**, no un despliegue verificado.

Componentes del código:

| Archivo / directorio | Función |
|---|---|
| robot_arm_controller/robot_arm_controller.ino | Firmware ESP32, comandos seriales, movimientos, límites y coreografías |
| control-center/backend/config.py | Especificaciones de servos, parámetros seriales/WebSocket y cámara |
| control-center/backend/main.py | Punto de entrada del servidor local: simulación o hardware |
| control-center/backend/controller.py | Control y comandos, Home y límites |
| control-center/backend/serial_manager.py | Comunicación con ESP32 |
| control-center/backend/joystick_manager.py | Joystick USB |
| control-center/backend/robot_state.py | Estado compartido y telemetría |
| control-center/backend/ws_server.py | WebSocket del estado/control, puerto 8765 |
| control-center/backend/perception.py | Percepción simulada, RealSense local o remota |
| control-center/backend/jetson_perception_node.py | Prototipo de nodo de nube remota de Jetson, puerto 8766 |
| control-center/frontend/src/RobotScene.jsx | Escena/gemelo digital 3D |
| control-center/frontend/src/robotModel.js | Modelo geométrico y mapeo del brazo |
| control-center/frontend/src/useRobotSocket.js | Cliente y reconexión WebSocket |
| control-center/backend/tests/ | Pruebas unitarias existentes |

El backend arranca en modo hardware de forma predeterminada. Para validación sin motores, elegir siempre explícitamente --mode simulation y --perception simulated u off, según la prueba.

Los requisitos del backend en el repositorio incluyen:

~~~text
pygame==2.6.1
pyserial==3.5
websockets==16.0
~~~

El frontend usa React, React Three Fiber, drei, Three.js y Vite 8. El README recomienda Python 3.12/3.13 y Node.js 20.19 o superior en el equipo que ejecute el stack moderno.

## 5. Compatibilidad: por qué no se puede ejecutar este backend con Python 3.6

El Python **del sistema de JetPack** es 3.6.9 y sus bibliotecas TensorRT pertenecen a ese entorno. El repositorio contiene características modernas incompatibles con Python 3.6, por ejemplo:

- from __future__ import annotations, incorporado después de Python 3.6.
- dataclasses como módulo estándar, incorporado después de Python 3.6.
- anotaciones como list[list[float]], no válidas como genéricos integrados en Python 3.6.
- uniones como float | None y asyncio.to_thread, de versiones posteriores.
- Dependencia websockets==16.0, incompatible con Python 3.6.
- El frontend Vite 8 requiere un Node.js moderno, que no se ha preparado en esta Jetson.

**Decisión vigente:**

- Conservar /usr/bin/python3 y el Python 3.6 de NVIDIA.
- Usar ~/robot-lab/.venv-jetson para bibliotecas NVIDIA y desarrollos pequeños compatibles con 3.6.
- Ejecutar inicialmente el backend moderno, frontend 3D y herramientas de agente en la Mac u otro equipo compatible.
- Diseñar, si hace falta, un servicio mínimo específico para Jetson compatible con su runtime o una estrategia explícita de Python moderno **sin** afectar las dependencias de JetPack; evaluar esta opción antes de instalar.
- No copiar sin revisar los comandos genéricos del manual (por ejemplo pip upgrade global) en la Jetson.

**El archivo jetson_perception_node.py todavía requiere adaptación/refactorización para Python 3.6 o ejecución en otro intérprete compatible; su existencia no demuestra que funcione.**

## 6. Estado instalado y acceso a la Jetson

| Área | Estado |
|---|---|
| Hardware Jetson Nano 2GB | Operativo |
| JetPack 4.6.1 / Ubuntu 18.04.6 / L4T R32.7.1 | Verificado |
| SSH por Ethernet | Probado |
| Nombre local | jetson-nano.local, probado |
| IP durante instalación | 192.168.100.60, dinámica |
| CUDA | 10.2.300, nvcc consultado |
| cuDNN | 8.2.1, paquete presente |
| TensorRT Python | 8.2.1.8, import correcto |
| OpenCV Python | 4.1.1, import correcto |
| Python sistema | 3.6.9 |
| pip global APT | 9.0.1 |
| venv NVIDIA | ~/robot-lab/.venv-jetson |
| pip dentro del venv | 21.3.1 |
| Repositorio local | ~/robot-lab/Brazo-robot |
| Rama Jetson | feat/jetson-nano-physical-ai |
| Cámara D435i en Jetson | Sin probar |
| librealsense/pyrealsense2 en Jetson | Sin instalar/verificar |
| PCA9685 conectado directamente a Jetson | **Sí, solamente conexión lógica I²C 3.3 V y pruebas de registros**; 0x40 responde |
| Movimiento de servos desde Jetson | No |
| IA autónoma / planeación | No |
| Paro de emergencia físico instalado | No confirmado; debe verificarse antes de energizar |

Ver [bitácora de instalación](06-bitacora-instalacion-jetson-nano.md) para el procedimiento, errores resueltos, comandos y resultados.

## 7. Control actual y joystick

El firmware ESP32 utiliza comunicación serial a 115200 baudios. Comandos definidos:

| Comando | Resultado |
|---|---|
| help | Ayuda |
| status | Estado interno |
| home | Mover hacia Home |
| s ID ANGULO | Establecer ángulo absoluto |
| d ID DELTA | Mover relativamente |
| homev ID ANGULO | Cambiar Home solo en RAM |
| range ID MIN MAX | Cambiar límites solo en RAM |
| saludo | Coreografía de saludo |
| rutina | Coreografía de siete poses |
| stop | Cancelar secuencia y ordenar regreso a Home |

Mapeo del joystick Genius Max Fighter F-23U:

| Control | Articulación / acción |
|---|---|
| Axis 0 | Base |
| Axis 1 | Hombro |
| Button 2 / 3 | Codo abajo / arriba |
| Hat izquierda / derecha | Muñeca vertical |
| Hat arriba / abajo | Giro de muñeca |
| Button 0 / 1 | Cerrar / abrir garra |
| Button 4 | Home |
| Button 5 | Saludo |
| Button 6 | Cancelar y Home |
| Button 7 | Rutina |

El botón de cancelación con regreso a Home y el comando stop **NO son un paro de emergencia físico**, pues pueden ordenar nuevos movimientos. Un interruptor de corte de potencia de los servos es requisito previo a pruebas autónomas.

## 8. Visión Intel RealSense D435i

Cámara prevista: Intel RealSense D435i, serie 926522071007; la documentación de hardware también registra identificador K38179-100. El objetivo de prueba es profundidad 640x480 a 30 fps, nube reducida de hasta 1,000 puntos y publicación aproximadamente a 8 Hz. Son parámetros **de diseño**, no medidas de rendimiento realizadas en la Jetson.

Faltan:

1. Conectar la D435i por USB 3 y verificar su detección.
2. Determinar versión compatible de librealsense/pyrealsense2 con JetPack 4.6.1 y ARM64.
3. Adaptar/ejecutar el nodo de percepción en un Python compatible.
4. Validar capturas y pérdidas de cuadros con memoria limitada.
5. Montar la cámara mecánicamente y calcular la transformación extrínseca cámara -> base.
6. Separar estrictamente percepción y capacidad para ordenar movimiento físico.

La nube RealSense sin calibración está en el sistema de coordenadas de la cámara; **no usarla para evitar colisiones o planear movimientos físicos** hasta disponer de calibración y validación.

El WebSocket de percepción previsto en el puerto 8766 no autentica ni cifra por defecto: solo usar en LAN de confianza o diseñar control de acceso antes de desplegar.

## 9. Ramas y decisiones en GitHub

| Referencia | Estado / propósito |
|---|---|
| main | Base estable del repositorio; commit de partida 8251aa9 |
| feat/raspberry-pi-4-direct-control | Experimento anterior de control directo con Raspberry Pi 4 |
| Pull request #4 | Abierto, **sin fusionar** con main |
| feat/jetson-nano-physical-ai | Rama nueva específica para Jetson; seleccionada localmente |

PR Raspberry Pi 4: https://github.com/Antonio-Richaud/Brazo-robot/pull/4

**No confundir** el PR Raspberry Pi con una integración Jetson: pines, bibliotecas GPIO, configuración I2C y validaciones son diferentes. Es posible reutilizar ideas de arquitectura, pero no asumir compatibilidad eléctrica ni de software.

**Práctica acordada:** desarrollar en la rama Jetson; no cambiar main ni incorporar el PR Raspberry Pi automáticamente. Los documentos 06 y 07 constituyen el punto de reanudación.

## 10. Reglas de seguridad que deben respetarse

- **No energizar ni mover servos** hasta disponer de una secuencia de prueba definida, topes comprobados, zona despejada y capacidad de cortar físicamente la potencia.
- Comprobar lógica I2C y tierras antes de conectar la fuente de los motores. No alimentar la Jetson desde la salida de potencia de servos.
- No conectar/desconectar servos mientras su fuente esté energizada.
- El firmware ESP32 existente escribe Home en el arranque, lo que puede producir un movimiento brusco si el brazo estaba en otra posición. En una adaptación Jetson, preferir desarmado por defecto, habilitación explícita y ausencia de PWM al iniciar.
- Telemetría angular es estimada, no posición real medida.
- No permitir que un agente de IA controle directamente PWM o puertos: todas sus acciones deben pasar por un validador independiente con límites, temporización, confirmación y paro físico.
- No usar información RealSense sin calibración para autonomía.
- Ubuntu 18.04 y JetPack 4.x son antiguos: reducir superficie de exposición de red y no abrir servicios a Internet.
- Conservar paquetes críticos de NVIDIA. No ejecutar apt upgrade/full-upgrade indiscriminadamente ni alterar Python del sistema.

## 11. Plan de trabajo por etapas (pendiente, no ejecutado)

### Fase A — Diagnóstico y conservación

- [x] Jetson inicia y admite SSH remoto.
- [x] Confirmar L4T/JetPack, CUDA, cuDNN, TensorRT y OpenCV.
- [x] Instalar pip/venv sin actualización masiva del sistema.
- [x] Crear y validar entorno NVIDIA.
- [x] Clonar el repositorio y seleccionar rama Jetson.
- [x] Registrar bitácora y estado de continuidad en GitHub.
- [x] Sincronizar en la Jetson los commits de documentación y herramienta PCA9685 hasta el commit 83f54b5; los cambios posteriores requerirán nuevo `git pull`.

### Fase B — Separar backend moderno y controlador de hardware

- [ ] Auditar el contrato actual RobotController/SerialManager/RobotState.
- [ ] Definir interfaz independiente de hardware (ESP32 serial, simulación, futuro adaptador Jetson).
- [x] Añadir sandbox Jetson de seis ejes sin hardware (`jetson/arm_simulation.py`) con armado matemático explícito y estado DISARMED inicial.
- [x] Ejecutar las 17 pruebas nuevas en Jetson con las nueve previas (26/26, `OK`, 0.013 s).
- [x] Confirmar la demostración `python3 jetson/arm_simulation.py --demo` en Jetson: trayectoria 90° → 125° en cinco pasos; `DISARMED`, `hardware_enabled: false`, sin I²C/GPIO.
- [ ] Integrar una interfaz de hardware con el backend moderno, sin permitir habilitación física todavía.
- [x] Validar en la Jetson (tests simulados) lógica de velocidades por articulación, timeout del watchdog cooperativo y bloqueo por FAULT.
- [ ] Diseñar límites de aceleración y watchdog independientes de la aplicación para el hardware real.
- [x] Ejecutar las pruebas del backend moderno en la Mac con Python 3.12.13: 7/7 `unittest` OK; servidor iniciado explícitamente en simulación, conexión TCP `127.0.0.1:8765` comprobada.
- [x] Instalar dependencias frontend, corregir 11 alertas de auditoría, validar lint y build en Mac: producción 0, desarrollo 6 moderadas en árbol ESLint/minimatch; commit `999367e` publicado en rama Jetson.
- [x] Abrir el dashboard 3D en `http://127.0.0.1:5173/` en Mac; el usuario confirmó que la interfaz se visualiza correctamente (paso 9.31).
- [x] Verificar handshake WebSocket y snapshot JSON del backend Mac en cliente Python 3.12 de solo lectura (paso 9.32): protocolo 2, runtime simulación, 6/6 ejes, `measured: false`, ESP32 desconectado.
- [x] Verificar visualmente el estado conectado del dashboard React: captura del usuario confirma `CONNECTED`, `simulation`, ESP32 sin enlace, percepción off, seis tarjetas de servos y modelo 3D renderizado (paso 9.33, comprobación parcial).
- [x] Verificar movimiento simulado de Base de 90° a 105° y respuesta del gemelo 3D desde el navegador (paso 9.33). **El usuario confirmó que funciona**; sin medir movimiento físico.
- [x] Probar visualmente la coreografía `Saludo` con `runtime_mode=simulation` en la Mac: el usuario comunicó «Sí parece que funciona bien» (paso 9.34).
- [x] Confirmar vía snapshot WebSocket **de solo lectura** después de Saludo el retorno exacto a Home (`current` y `target`) de los seis servos y `mode=manual` (paso 9.35; **6/6 OK**, `runtime_mode=simulation`).
- [x] Estudiar y probar pines J6 y comunicación I2C PCA9685 en Jetson Nano 2GB, sin alimentar motores.

### Fase C — Integración control físico

- [x] Comprobar comunicación I2C 0x40, registros, 50 Hz y FULL OFF sin alimentación de servos (no se midieron niveles eléctricos con instrumento).
- [x] Incorporar utilidad inicial de diagnóstico y FULL OFF, sin API de armado (jetson/pca9685_safe.py; pruebas unitarias simuladas).
- [x] Validar `python3 jetson/pca9685_safe.py status` sobre la Jetson real: MODE1=0x01, MODE2=0x04, PRE_SCALE=0x79, FULL OFF 16/16.
- [x] Ejecutar las nueve pruebas unitarias con Python 3.6 en la Jetson real (9/9, `OK`, 0.003 s).
- [x] Validar en hardware real la acción `disable-all`: escritura global aceptada y 16/16 canales FULL OFF.
- [ ] Implementar futuro adaptador Jetson de control, con armado explícito y PWM deshabilitado por defecto.
- [ ] Añadir interruptor de corte físico de potencia y protocolo de arranque seguro.
- [ ] Probar cada servo individualmente con fuente externa y límites calibrados.
- [ ] Validar Home, telemetría, pérdida de conexión y paro físico.

### Fase D — Percepción 3D

- [ ] Comprobar USB 3 y conexión real de Intel D435i.
- [ ] Elegir/instalar versión compatible de librealsense para ARM64/JetPack 4.x.
- [ ] Adaptar nodo de percepción y probar únicamente publicación de datos.
- [ ] Calibrar extrínsecos cámara -> robot_base.
- [ ] Agregar segmentación, obstáculos y pruebas de confiabilidad.

### Fase E — Gemelo digital, gestos y agente

- [ ] Sincronizar estado del brazo y mostrar explícitamente posición estimada.
- [ ] Verificar el dashboard 3D existente en Mac en modo simulación y sin joystick antes de integrar telemetría Jetson.
- [ ] Definir e implementar puente de telemetría solo lectura desde el simulador Jetson al backend moderno; sin habilitar control físico.
- [ ] Probar comandos manuales/joystick y visualización en simulación.
- [ ] Añadir reconocimiento de gestos mediante una arquitectura compatible con los recursos.
- [ ] Introducir agente que genere propuestas de movimiento, sometidas a autorización y límites.
- [ ] Habilitar operaciones autónomas únicamente con supervisión y seguridad física verificadas.

## 12. Cómo reanudar en otra sesión sin perder el contexto

**En un nuevo chat o sesión de soporte, aportar:**

> Estamos trabajando en Antonio-Richaud/Brazo-robot, rama feat/jetson-nano-physical-ai. La Jetson Nano 2GB ya tiene JetPack 4.6.1, Ubuntu 18.04.6, L4T R32.7.1, Python 3.6.9, CUDA 10.2.300, TensorRT Python 8.2.1.8, OpenCV 4.1.1 y el venv ~/robot-lab/.venv-jetson con pip 21.3.1; SSH funciona en antonio@jetson-nano.local. El repo está en ~/robot-lab/Brazo-robot. Leer docs/06-bitacora-instalacion-jetson-nano.md, docs/07-estado-y-continuidad-del-proyecto.md, docs/08-jetson-pca9685-i2c-pruebas.md y docs/09-jetson-simulacion-seis-servos.md. La D435i no se ha conectado; el PCA9685 SÍ se ha conectado por I2C 0x40 a 3.3 V (OE alto), pero no se han movido servos, el backend actual necesita Python moderno y no debe instalarse sobre Python 3.6. Continuar **un paso a la vez**, solicitando salidas de comandos antes de proceder; mantener main intacta.

Comandos mínimos de arranque de sesión:

~~~bash
# Desde la Mac:
ssh antonio@jetson-nano.local

# Dentro de la Jetson:
cd ~/robot-lab/Brazo-robot
git status -sb
git pull --ff-only origin feat/jetson-nano-physical-ai
git log -1 --oneline
python3 jetson/pca9685_safe.py status  # Diagnostico solamente, sin escribir

# Comprobar entorno NVIDIA sin instalar nada:
source ~/robot-lab/.venv-jetson/bin/activate
python -m pip --version
python -c "import cv2, tensorrt; print(cv2.__version__, tensorrt.__version__)"
deactivate
~~~

Si el estado Git tiene cambios locales, **no hacer reset --hard** ni descartar archivos: revisar git status antes de sincronizar.

**Preferencia de ejecución para este proyecto:** trabajar paso a paso, con comandos concretos y validación de la salida real antes de avanzar. No desplegar paquetes, hardware o cambios de arquitectura como si estuvieran aprobados o ya probados.

## 13. Documentos canónicos y límites de lo documentado

- [README principal](../README.md)
- [01 — Hardware y conexiones](01-hardware-y-conexiones.md)
- [02 — Firmware ESP32](02-firmware-esp32.md)
- [03 — Control Center](03-control-center.md)
- [04 — Diseño de RealSense en Jetson](04-realsense-jetson.md)
- [05 — Manual de uso y pruebas](05-manual-de-uso-y-pruebas.md)
- [06 — Bitácora de instalación efectiva de la Jetson](06-bitacora-instalacion-jetson-nano.md)
- [08 — Cableado Jetson J6, diagnóstico PCA9685 y seguridad](08-jetson-pca9685-i2c-pruebas.md)
- [09 — Simulación aislada de seis ejes en Python 3.6](09-jetson-simulacion-seis-servos.md)

Este documento incorpora los resultados confirmados hasta el 30-10-2026; versiones, IP, servicios y hardware deben volverse a consultar si transcurre tiempo o se cambia la instalación.

## 14. Avances Mac: línea base del Control Center (30-10-2026)

Se siguieron los pasos 9.18–9.30, validados con salidas reales en la MacBook Air. **No constituyen pruebas de integración Jetson→Mac ni movimiento físico**.

| Área | Confirmado |
|---|---|
| Herramientas Mac | Python 3.14.7 predeterminado, Python 3.12.13 para backend, Node.js 24.18.0, npm 11.16.0 |
| Rama de trabajo | `feat/jetson-nano-physical-ai`, limpia al cerrar el commit de dependencias |
| Backend | `.venv` Python 3.12.13, `pygame 2.6.1`, `pyserial 3.5`, `websockets 16.0`, `pip check` OK |
| Tests backend | **7/7 OK** |
| Servidor backend | `ROBOT_WS_HOST=127.0.0.1 python main.py --mode simulation --perception off --no-joystick`, Python escuchando `127.0.0.1:8765`, TCP OK |
| Frontend | `npm ci` y `npm audit fix` sin `--force`; `npm run lint` OK; `npm run build` OK con Vite 8.3.5 (571 módulos) |
| Auditoría npm | Inicial: 17 (10 moderadas, 7 altas); posterior: 6 moderadas de desarrollo (ESLint/`minimatch`); **producción 0** |
| GitHub | Commit `999367e`: solo `control-center/frontend/package-lock.json`, publicado en la rama de trabajo; `main` no modificado |

**Alcance de la comprobación:** el frontend ya se inició y el usuario confirma que la interfaz 3D se visualiza bien en `127.0.0.1:5173` (paso 9.31). Escuchar TCP y ver la interfaz **no equivale** a verificar el protocolo WebSocket o que los seis servos reciban estado del backend. El siguiente paso es recibir un snapshot WebSocket con un cliente local **de solo lectura**, verificar `runtime_mode=simulation`, nombres de los seis ejes y `measured=false`. Queda pendiente investigar `minimatch` y la versión de ESLint sin soporte sin usar actualizaciones forzadas.

**Paso 9.32 registrado:** cliente WebSocket en Mac conectado a `ws://127.0.0.1:8765` y validó `protocol_version=2`, `runtime_mode=simulation`, `mode=manual`, `connected=false` para ESP32, seis servos con `measured=false`. Bases de simulación: base 90°, hombro 50°, codo 165°, muneca1 10°, muneca2 170°, garra 40°. La prueba fue únicamente de recepción de telemetría, sin envío de órdenes. **Próximo paso:** verificar el movimiento del eje Base hacia 105° en la UI, solo con `Runtime=simulation` y `ENLACE LOCAL=connected`; evaluar cambios `current/target` y escena 3D. El nodo Jetson permanece independiente, OE alto y potencia externa apagada.

**Comandos históricos del arranque en Mac (ya ejecutados):**
```bash
cd ~/Documents/GitHub/Brazo-robot/control-center/frontend
npm run dev -- --host 127.0.0.1
```
Abrir la URL local que imprima Vite (habitualmente `http://127.0.0.1:5173/`), comprobar visualización 3D, estado de conexión y consola. Mantener el backend local activo, `OE` alto (3.3 V), fuente externa de servos apagada y la Jetson sin nuevos servicios de red.

## 15. Cierre de línea base Mac y comienzo de telemetría Jetson (30-10-2026)

**Paso 9.34:** usuario confirmó visualmente que la coreografía virtual `Saludo` parece funcionar bien. La comprobación exacta quedó pendiente hasta el paso siguiente.

**Paso 9.35, comprobado con la salida real del cliente WebSocket de solo lectura:** tras la coreografía, el backend regresó a `runtime_mode: simulation`, `mode: manual` y **todos los seis servos tienen `current == target == home`**: base 90, hombro 50, codo 165, muneca1 10, muneca2 170, garra 40 grados. Mensaje final: `RESULTADO: HOME VERIFICADO`. El recorrido UI→WebSocket→backend simulado→UI 3D y el retorno a Home quedan confirmados en la Mac. Ninguna posición es una lectura física.

**Siguiente paso 9.36:** confirmar que la Mac puede ejecutar por SSH una lectura JSON del simulador Python 3.6 existente en la Jetson, sin modificar archivos, instalar paquetes, abrir un puerto nuevo, acceder a I²C ni encender servomotores. Se pretende un transporte de telemetría **de lectura desde Mac mediante SSH existente**, no un servidor sin autenticación en Jetson. En una fase posterior diseñar un modo separado de telemetría remota que rechace comandos de movimiento; no reutilizar `simulation` como si fueran datos de Jetson ni aceptar comandos remotos hacia PWM.

Permanecen pendientes validación de conectividad SSH actual, implementación del puente, manejo de desconexiones, pruebas de aislamiento, watchdog independiente de hardware, corte físico de alimentación y calibración de servos. `OE` debe mantenerse alto a 3.3 V y V+ de los servos sin alimentación. Trabajar solo en `feat/jetson-nano-physical-ai`; `main` queda intacta.

## 16. SSH y emisor de telemetria JSONL de Jetson (30-10-2026)

**Paso 9.36, confirmado:** SSH Mac->Jetson con autenticacion por contrasena; Python 3.6.9; `ArmSimulation().snapshot()` enviado a Mac en JSON, seis ejes, `DISARMED`, `hardware_enabled=false`, `measured=false`. La validacion concluyo `JETSON_SIMULATION_READONLY_OK`. La advertencia SSH poscuantica no impidio la sesion.

**Paso 9.37, comprobado en la Jetson real (30-10-2026):** `jetson/telemetry_stream.py` emitió 13 tramas JSONL por stdout (Base matemática 90→125→90, `DISARMED` final), y `jetson/tests/test_telemetry_stream.py` elevó el total de pruebas Jetson a **36/36 OK en 0.064 s**. La salida comprobó `JETSON_TELEMETRY_JSONL_OK` y ninguna habilitación de hardware.

**Separacion de seguridad:** SSH es el unico transporte remoto usado hasta ahora; no se abren servidores TCP en Jetson, ni existen comandos de control remoto de motores. El frontend sigue funcionando con simulacion local de Mac, **no** alimentado por datos Jetson. Para integrarlo se requiere validador de esquema, modo de monitor remoto solo lectura con controles deshabilitados y manejo de desconexion.

**Paso siguiente:** validar en la Mac un receptor pasivo de las 13 tramas JSONL enviadas por SSH; únicamente después de pasar pruebas y validar datos remotos se diseñará un modo de visualización con controles deshabilitados. Mantener OE alto, alimentación V+ de servos apagada y `main` sin cambios.

## 17. Paso 9.38: validador pasivo en Mac (pendiente de pruebas)

El usuario verificó sobre la Jetson Nano 2GB: rama `feat/jetson-nano-physical-ai` actualizada mediante fast-forward, **36/36 tests OK (0.064 s)**, y demostración de 13 tramas `JSONL` con `Base 90→125→90`, `DISARMED` inicial/final y marcador `JETSON_TELEMETRY_JSONL_OK`. Las tramas provienen exclusivamente de simulación.

**Implementado directamente en GitHub, por verificar en Mac:**

- `control-center/backend/jetson_telemetry_reader.py`: validador **solo lectura** de stdin, sin SSH interno, sin acceso a red, GPIO, I²C, PWM o comandos WebSocket. Acepta exclusivamente `--stdin-demo`, 13 tramas v1 de `source=jetson_simulation`; rechaza `hardware_enabled`, `measured=true`, versiones, IDs/canales y ángulos desconocidos, secuencias inválidas, tamaño excesivo y retorno incorrecto a Home.
- `control-center/backend/tests/test_jetson_telemetry_reader.py`: **22 tests** nuevos con reloj matemático simulado. Los **29 tests esperados del backend Mac (7+22)** todavía deben ejecutarse en la Mac antes de afirmarse aprobados.
- La consola Mac abrirá el transporte SSH autenticado **de forma externa** y pasará stdout al validador con `|` y `set -o pipefail`. Ningún servicio nuevo en Jetson. Backend WebSocket y dashboard Mac **todavía no consumen** estas tramas.

**Próxima acción verificada por el usuario:** sincronizar la rama en la Mac, ejecutar pruebas del backend y después el flujo `ssh ... python3 jetson/telemetry_stream.py --demo | python jetson_telemetry_reader.py --stdin-demo`. Esperado `MAC_JETSON_TELEMETRY_READONLY_OK`, todavía **no ejecutado**. Mantener `main` intacta, OE alto 3.3 V y V+ sin energizar.

## 18. Paso 9.38 verificado y replay Jetson 9.39 (30-10-2026)

**Mac: 29/29 tests OK (0.015 s)**. Flujo real SSH `Jetson → Mac` validado: `source=jetson_simulation`, esquema v1, 13 tramas de Base 90→125→90, `DISARMED` final, `hardware_enabled=false`, `measured=false`, salida `MAC_JETSON_TELEMETRY_READONLY_OK`. Se trata exclusivamente de la demo matemática, no de lectura física o telemetría en vivo.

**Paso 9.39 desarrollado en GitHub, sin pruebas de ejecución todavía:** nuevo `control-center/backend/jetson_demo_monitor.py` que recibe JSONL desde stdin, lo valida íntegramente y reproduce los 13 estados con WebSocket **solo en `127.0.0.1:8767`**, separado del backend habitual en 8765. No abre SSH ni conecta serial, I²C, GPIO o PWM. El WebSocket tiene `command_handler=None` y publica `runtime_mode=jetson_replay` / `mode=monitor`. El frontend `App.jsx` etiqueta la reproducción y deshabilita Home, Saludo, Rutina, Cancelar y sliders mientras el modo esté activo. Se añadieron 10 tests en `control-center/backend/tests/test_jetson_demo_monitor.py`.

**Pendientes de confirmar antes de abrir el monitor:** 39 tests backend Mac y validaciones `npm run lint` / `npm run build`. Después ejecutar SSH→monitor pasivo e iniciar la segunda instancia de frontend contra 8767 para comprobar animación de reproducción.

**No confundir:** reproducir frames Jetson después de haberlos recibido no implica streaming continuo del estado Jetson, feedback angular medido ni seguridad funcional del brazo físico. El modo real de control por hardware se mantiene fuera de esta prueba; el OE permanece alto (3.3 V), V+ apagada, `main` intacta.

## 19. Paso 9.39 validado y arranque 9.40 pendiente (30-10-2026)

**La Mac sincronizó la rama hasta `87ddb8a` y el usuario proporcionó salidas reales de validación:**

- `control-center/backend/.venv/bin/python -m unittest discover -s tests -v` desde `control-center/backend`: **39/39 pruebas aprobadas en 0.030 s** (`OK`).
- `npm run lint` desde `control-center/frontend`: finalizó sin errores.
- `npm run build`: Vite **8.3.5**, **571 módulos**, compilación terminada correctamente en **539 ms**. El artefacto de escena 3D sigue grande, sin fallo de compilación.
- `git status -sb`: rama `feat/jetson-nano-physical-ai` sincronizada con su remoto, sin modificaciones locales.
- Estas verificaciones incluyen 10 pruebas de `jetson_demo_monitor.py` (sin abrir puertos), las 22 del validador pasivo y 7 anteriores. **No** prueban aún la apertura del monitor en puerto 8767 ni la visualización de tramas remotas en el navegador.

**Siguiente paso 9.40 — arranque controlado del monitor:** desde Mac, abrir una terminal independiente y ejecutar la tubería `ssh -T antonio@jetson-nano.local 'cd "$HOME/robot-lab/Brazo-robot" && python3 jetson/telemetry_stream.py --demo' | control-center/backend/.venv/bin/python control-center/backend/jetson_demo_monitor.py --stdin-demo` con `set -o pipefail`. El monitor debe recibir y **validar las 13 tramas completas antes de abrir** `ws://127.0.0.1:8767`. Se espera el mensaje `JETSON_REPLAY_MONITOR_READY`, todavía no confirmado. El proceso permanece activo hasta `Ctrl+C`.

**Después y solo cuando 9.40 sea confirmado:** iniciar una segunda instancia de Vite, en `127.0.0.1:5174`, configurando `VITE_ROBOT_WS_URL=ws://127.0.0.1:8767` para comprobar el gemelo 3D y los botones/sliders bloqueados. La instancia normal en 5173 usa el backend local en 8765.

**Aclaración fundamental:** esta fase **reproduce en bucle** 13 cuadros de simulación generados en Jetson y transmitidos una sola vez por SSH; no es una transmisión continua del estado real de la Jetson ni controla servos. `OE` alto (3.3 V), V+ apagada y `main` sin alterar.

## 20. Paso 9.40 confirmado: monitor de reproducción Jetson en Mac (30-10-2026)

El usuario ejecutó desde su Mac la tubería SSH autenticada hacia `antonio@jetson-nano.local`, que emite una demostración matemática de 13 tramas JSONL, y las entregó por stdin a `control-center/backend/jetson_demo_monitor.py --stdin-demo`. Se sincronizó la rama de trabajo hasta `7a9ef66` sin conflictos.

**Salida real confirmada:**

```text
JETSON_REPLAY_MONITOR_READY ws://127.0.0.1:8767
Modo: replay Jetson matematico / solo lectura / sin motores. Detener con Ctrl+C.
```

Esto confirma que el monitor pasó la validación de los datos de demostración y abrió su WebSocket local de reproducción; todavía **no confirma** que el dashboard reciba sus actualizaciones, que el modelo 3D se anime, ni que los botones y deslizadores estén visualmente deshabilitados.

**Paso 9.41 pendiente:** sin cerrar el monitor ni los servicios originales, abrir otra terminal de Mac y ejecutar `VITE_ROBOT_WS_URL=ws://127.0.0.1:8767 npm run dev -- --host 127.0.0.1 --port 5174 --strictPort` dentro de `control-center/frontend`. Visitar `http://127.0.0.1:5174/` y confirmar `CONNECTED`, `runtime_mode=jetson_replay`, `mode=monitor`, cambio visual repetido de Base entre 90° y 125°, y controles Home/Saludo/Rutina/Cancelar/sliders deshabilitados. La UI original en 5173 sigue apuntando al backend local en 8765.

La captura es solo **replay de una simulación generada en Jetson** y no streaming de sensores, medida física ni control de servos. OE sigue alto (3.3 V), alimentación externa de motores desconectada/apagada y `main` intacta.

## 21. Paso 9.41: replay Jetson visible en React; maximo por comprobar (30-10-2026)

**Éxito visual confirmado:** el usuario abrió `http://127.0.0.1:5174/` y confirmó que el brazo 3D se ve bien y su Base se mueve de forma repetida. El modo debería leer el servidor Mac `ws://127.0.0.1:8767` y deshabilitar acciones al detectar `jetson_replay` / `monitor`. La confirmación del movimiento y renderizado 3D **no equivale a comprobar los valores o bloqueo de cada control**.

**Diferencia reportada:** el usuario describió un movimiento **90°→180°→90°**, mientras que la demo emitida en la Jetson y el código de la rama especifican **90°→125°→90°**. El límite de Base es 170° y `robotModel.js` calcula rotación 3D relativa a Home (Base 90°). No hay evidencia de lectura real de 180° ni movimiento físico: tratar el desfase como **pendiente de diagnóstico**, no corregir por suposición.

**Próximo paso 9.42:** prueba WebSocket Mac de solo recepción en puerto 8767 durante unos segundos, registrar mínimo/máximo de `servos.base.current` y `target`, confirmar `runtime_mode=jetson_replay`, `mode=monitor`, origen simulado y seis ejes `measured=false`. Si máximo 125°, aclarar que «180» fue estimación visual o una lectura de UI distinta y pedir captura del valor exacto. Confirmar también que todos los controles aparecen deshabilitados.

**Seguridad y alcance:** WebSocket de monitor de solo lectura en loopback; replay matemático, sin servos ni cámara. OE alto a 3.3 V, alimentación de motores apagada, `main` intacta.

## 22. Paso 9.42: 27 lecturas WebSocket con rango correcto (30-10-2026)

**Verificado por ejecución real en la Mac:** un cliente Python exclusivamente de lectura recibió 27 mensajes del WebSocket de replay `ws://127.0.0.1:8767`. Todos cumplieron `runtime_mode=jetson_replay`, `mode=monitor`, seis articulaciones y `measured=false` en cada articulación. Se observaron Base `[90, 97, 104, 111, 118, 125]` grados; mínimo 90°, máximo **125°**, objetivos `[90,125]` y salida `REPLAY_BASE_90_125_OK`.

Esto resuelve el alcance **numérico** de la diferencia entre los «180°» descritos visualmente y los 125° configurados: la telemetría **no publicó 180°**. No se estableció si esa observación fue estimación visual o una lectura distinta; no alterar parámetros sin evidencia adicional.

**Siguiente paso 9.43:** comprobar en el navegador los cuatro botones de acción y los seis sliders deshabilitados durante `jetson_replay / monitor`. El bloqueo está implementado en `App.jsx` y el WebSocket no tiene handler de comandos, pero la confirmación visual de los controles aún no se ha recibido. Esta secuencia es simulación/replay de Jetson a Mac, **no** medición física ni control de motores. OE 3.3 V, V+ apagada y `main` sin cambios.

## 23. Paso 9.43: controles UI de replay bloqueados (confirmado, 30-10-2026)

**Evidencia:** captura real de la consola de Chrome compartida por el usuario, tomada con el segundo dashboard en `http://127.0.0.1:5174/`. Se ejecutó una inspección DOM de `.action-grid button` y `.servo-list input[type="range"]`: los cuatro botones **Home, Saludo, Rutina y Cancelar/Home** devolvieron `disabled=true`, y **los seis sliders** también: `Deslizadores bloqueados: 6 de 6`. Marcador exacto: `VERIFICACION: CONTROLES_BLOQUEADOS_OK`.

**Resultado:** el bloqueo visual de los 10 controles en el modo `jetson_replay` queda comprobado en el navegador. El servidor WebSocket de replay en Mac `127.0.0.1:8767` tiene `command_handler=None` de acuerdo con el código de la rama, y el modo no utiliza ESP32 ni control físico. No atribuirle pruebas de bloqueo del resto de interfaces o seguridad mecánica/electrónica.

**Observación adicional en la captura:** aparecen muchas advertencias repetidas de Three.js (`THREE.WebGLShadowMap: PCFSoftShadowMap has been deprecated. Using PCFShadowMap instead.`), con contador superior de aproximadamente **1163 advertencias** y un indicador de **1 error** cuyo mensaje no se ve. `undefined` después de ejecutar la función de consola es el resultado normal de una IIFE y no evidencia de error. El motivo del error rojo y la recurrencia de las advertencias deben diagnosticarse por separado; no se deben declarar resueltos.

**Próxima tarea recomendada:** inspeccionar el mensaje del error rojo de la consola y, posteriormente, corregir el uso de sombras obsoletas de Three.js con cambios mínimos y pruebas `lint`/`build`, sin alterar la geometría ni comportamiento del brazo 3D. Trabajar solo en la rama `feat/jetson-nano-physical-ai`, sin habilitar PWM, fuente V+ ni bajar OE.

## 24. Paso 9.44: favicon 404 y advertencias WebGL (corrección pendiente de validar, 30-10-2026)

**Diagnóstico con captura real de Chrome DevTools de `http://127.0.0.1:5174/`:** el único error rojo visible es `Failed to load resource: the server responded with a status of 404 (Not Found)`, ruta `:5174/favicon.ico:1`. No corresponde a WebSocket, Python, servos ni cálculo de la posición. La consola además muestra más de 1,300 advertencias repetidas `THREE.WebGLShadowMap: PCFSoftShadowMap has been deprecated. Using PCFShadowMap instead.`.

**Cambios mínimos ya incorporados directamente en rama `feat/jetson-nano-physical-ai`:**

- Se creó `control-center/frontend/public/favicon.svg`, icono vectorial local con la paleta del dashboard.
- Se añadió a `control-center/frontend/index.html` un enlace HTML explícito `<link rel="icon" type="image/svg+xml" href="/favicon.svg" />`, para que el navegador solicite la ruta válida en lugar de buscar implícitamente `/favicon.ico`.
- En `control-center/frontend/src/RobotScene.jsx` se definió una configuración constante `SHADOW_SETTINGS = { type: THREE.PCFShadowMap }` y se pasó al `<Canvas>` mediante `shadows={SHADOW_SETTINGS}`. Evita seleccionar `PCFSoftShadowMap`, deprecado desde Three.js r182, y conserva las sombras y toda la geometría existente.
- No se modificaron el modelo cinemático, las seis articulaciones, límites, backend, PWM, seguridad del monitor ni el protocolo SSH/WebSocket.

**Pendiente de pruebas reales:** en Mac, `git pull --ff-only`, `npm run lint`, `npm run build`, `curl -I http://127.0.0.1:5174/favicon.svg` tras recarga, y Chrome DevTools con consola limpiada y recarga de página para verificar que desaparezcan la petición 404 del favicon y la advertencia de PCFSoftShadowMap. No declarar resuelto hasta recibir la salida/captura.

**Nota:** el `undefined` mostrado tras ejecutar la función de inspección en DevTools es normal; el error 404 era un recurso web faltante. Mantener 8767 como monitor solo lectura y conservar OE alto a 3.3 V y V+ apagada; `main` intacta.

## 25. Paso 9.45: lint/build y favicon HTTP 200 confirmados (30-10-2026)

**Salida de terminal recibida de la Mac:** el usuario actualizó la rama `feat/jetson-nano-physical-ai` con fast-forward `d3d0e27..45cd2ff`, incorporando `index.html`, el nuevo `public/favicon.svg`, `RobotScene.jsx` y la documentación. Desde `control-center/frontend`, ejecutó `npm run lint` (ESLint finalizó sin errores), `npm run build` (Vite 8.3.5, **571 módulos**, compilación exitosa en **539 ms**) y `curl` a `http://127.0.0.1:5174/favicon.svg` (**`FAVICON_HTTP_200`**).

**Conclusión limitada:** el recurso SVG ya se entrega por HTTP 200 y el cambio de sombras compila correctamente. **Todavía no consta una inspección nueva de DevTools** después de limpiar la consola y recargar: no afirmar aún que hayan desaparecido definitivamente el antiguo 404 de `/favicon.ico` o los avisos de `PCFSoftShadowMap` del navegador.

**Paso siguiente 9.46:** con el monitor Jetson `:8767` y el frontend `:5174` activos, abrir DevTools, desactivar `Preserve log` si estuviera habilitado, limpiar la consola, recargar `http://127.0.0.1:5174/` y observar durante varios segundos nuevos errores o advertencias. Verificar que la animación continúa y los controles siguen deshabilitados. Solicitar únicamente el resultado de esa inspección. No cambiar servos, backend ni geometría.

**Seguridad:** la reproducción se basa en datos matemáticos de Jetson; no hay medición física ni habilitación de PWM. OE alto a 3.3 V, fuente externa apagada y `main` intacta.

## 26. Paso 9.46: sin errores visibles; advertencias ocultas por filtro (30-10-2026)

El usuario compartió una captura posterior al cambio de favicon SVG y `THREE.PCFShadowMap`, desde `http://127.0.0.1:5174/`, que muestra el gemelo digital 3D renderizado, `CONNECTED`, etiqueta `MONITOR`, `runtime_mode=jetson_replay` y ninguna línea de error roja visible. El favicon ya había devuelto `FAVICON_HTTP_200`; el anterior error 404 no aparece en esta captura.

**Límite de la evidencia:** DevTools está filtrado como **`Solo Errores`**; la barra superior de Chrome muestra **2 advertencias** y **`5 ocultos`**. Por tanto, es correcto afirmar que no hay errores rojos visibles en esta vista, pero **todavía no** que la consola esté totalmente libre de advertencias o que la deprecación `PCFSoftShadowMap` haya desaparecido en tiempo de ejecución.

**Siguiente comprobación mínima:** cambiar el filtro de consola a **todos los niveles** (`Niveles predeterminados`), limpiar los registros y recargar la página; verificar si reaparece `PCFSoftShadowMap` o surge otra advertencia. Solicitar el contenido o captura de los avisos nuevos. No tocar backend, servos, geometry 3D ni el control de la Jetson durante esta comprobación.

El monitor continúa siendo replay matemático de solo lectura; mantener OE alto a 3.3 V, potencia de servos apagada y `main` intacta.

## 27. Paso 9.47: advertencias WebSocket / THREE.Clock diagnosticadas (30-10-2026)

**Captura del navegador compartida por el usuario con niveles personalizados:** el segundo dashboard en `127.0.0.1:5174` sigue renderizando el gemelo 3D, en modo `MONITOR`, con estado `CONNECTED`. No aparecen el anterior error 404 de favicon ni los avisos repetitivos `PCFSoftShadowMap`: ambas correcciones de los pasos 9.44-9.46 quedan confirmadas visualmente. Sí aparecen dos advertencias nuevas/distintas:

1. `WebSocket connection to 'ws://127.0.0.1:8767/' failed: WebSocket is closed before the connection is established`, referida a `useRobotSocket.js`. El código que se leyó de la rama abre `new WebSocket(url)` inmediatamente en un `useEffect` y ejecutaba `socketRef.current?.close()` durante su limpieza. `src/main.jsx` usa `React.StrictMode`, el cual monta/limpia/vuelve a montar efectos durante el desarrollo. Por lo tanto, este patrón puede cerrar un socket todavía `CONNECTING` y emitir la advertencia, incluso cuando el enlace se establece finalmente.
2. `THREE.THREE.Clock: This module has been deprecated. Please use THREE.Timer instead.`, enlazada con la línea del `<Canvas>` en `RobotScene.jsx`. La dependencia `@react-three/fiber` 9.x crea internamente un `THREE.Clock` y Three.js r183 lo marcó obsoleto. El proyecto no instancia directamente `THREE.Clock`; es una advertencia pendiente de migración upstream. No silenciar mensajes, no degradar Three.js ni cambiar React Three Fiber a una versión mayor experimental solo para ocultarla.

**Corrección de código aplicada en GitHub, pendiente de probar en Mac:** `control-center/frontend/src/useRobotSocket.js` ahora utiliza estado de ciclo de vida aislado por efecto, pospone el primer `new WebSocket()` al siguiente macrotask mediante `window.setTimeout(connect, 0)` (así Strict Mode puede cancelar su efecto inicial), y evita `socket.close()` mientras esté en estado `CONNECTING`; si se desmonta, `onopen` lo cierra después de establecer la conexión. Mantiene reconexión exponencial y el envío de órdenes existente sin ampliarlas. Este cambio no afecta al monitor remoto ni al ESP32.

**Próximo paso:** Mac `git pull --ff-only` de `feat/jetson-nano-physical-ai`, `npm run lint` + `npm run build` y DevTools en la segunda instancia 5174 tras limpiar consola/recargar. Verificar si desaparece la advertencia de WebSocket, si `CONNECTED` y la animación 3D continúan, y si permanece el aviso upstream `THREE.Clock` (conocido/no crítico). **No afirmar resultado antes de nueva evidencia.**

Seguridad: la reproduccion es matemática, con controles bloqueados y WebSocket del monitor sin comando. OE alto (3.3 V), servos sin alimentación y rama `main` intacta.

## 28. Paso 9.48: lint y build del cliente WebSocket correctos (30-10-2026)

El usuario confirmó mediante salida real de la Mac que el cambio de `control-center/frontend/src/useRobotSocket.js` se actualizó por `git pull --ff-only` desde `45cd2ff` hasta `2cf0046`, sin conflictos. En `control-center/frontend`, `npm run lint` finalizó sin errores; `npm run build` (Vite 8.3.5) compiló **571 módulos correctamente en 467 ms**, con nuevos hashes de bundles `index-BtmcOHbO.js` y `RobotScene-DPwhWKWV.js`.

**Alcance:** queda confirmado que el nuevo ciclo de conexión WebSocket no rompe el lint ni la compilación. **No está verificado aún** que desaparezca en Chrome la advertencia `WebSocket is closed before the connection is established`, que se mantenga `CONNECTED` tras recarga, o que continúe la animación; se requiere una prueba de ejecución en el dashboard `http://127.0.0.1:5174/` con DevTools (todos los niveles, limpiar y recargar). El aviso `THREE.Clock` es un asunto separado de dependencia upstream y puede continuar sin impedir la funcionalidad.

**Siguiente comprobación 9.49:** observar consola del segundo dashboard con el monitor WebSocket `8767` activo; confirmar ausencia de aviso de cierre temprano, enlace `CONNECTED`, escena animada y controles bloqueados. Mantener `main` intacta, OE alto a 3.3 V y potencia externa de servos apagada.

## 29. Paso 9.49: enlace WebSocket sin cierre prematuro en Chrome (30-10-2026)

**Evidencia visual aportada por el usuario:** captura nueva de Chrome DevTools del dashboard de reproducción en `127.0.0.1:5174` después de integrar el cambio de `useRobotSocket.js` y recargar. La interfaz muestra `ENLACE LOCAL: CONNECTED`, etiqueta `MONITOR`, `runtime_mode=jetson_replay` y el gemelo 3D renderizado. La consola muestra únicamente **una advertencia visible**: `THREE.THREE.Clock: This module has been deprecated. Please use THREE.Timer instead.` enlazada al montaje `<Canvas>` de `RobotScene.jsx`.

**Resultado del paso 9.49:** ya no aparece la advertencia `WebSocket is closed before the connection is established` que motivó el cambio de ciclo de vida en React StrictMode. Tampoco se ven el 404 de favicon ni los avisos repetitivos `PCFSoftShadowMap`. El resultado de conexión y renderizado está comprobado por captura; una imagen estática no mide por sí sola la continuidad del movimiento, que ya había sido validada anteriormente en el paso 9.41.

**Advertencia residual:** `THREE.Clock` proviene de la compatibilidad de React Three Fiber con Three.js reciente; no hay llamada directa a `THREE.Clock` en la aplicación. No mutearla, degradar Three.js ni forzar versiones mayores sin un plan y pruebas de regresión. No se trata de una falla de hardware o del enlace Jetson.

**Próximo paso 9.50 recomendado:** comprobar recuperación ante pérdida de enlace del monitor de reproducción: detener con `Ctrl+C` solo el proceso del monitor `:8767`, observar que la UI pasa de `CONNECTED` a `reconnecting` y mantiene sus controles deshabilitados. Verificar la recuperación tras reactivar el monitor en un paso posterior, sin enviar órdenes ni habilitar hardware.

Conservar OE alto a 3.3 V, servos sin alimentación externa, monitor matemático solo lectura y rama `main` intacta.
