# Estado del proyecto y documento de continuidad — Brazo Robot + Jetson Nano

**Fecha de corte inicial:** 26 de octubre de 2026  
**Última actualización:** 30 de octubre de 2026 (I²C, `status`, `disable-all` y 9/9 pruebas unitarias verificados en Jetson)  
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
- **No** se ha instalado el runtime completo, conectado la D435i, energizado el brazo desde Jetson ni movido servos.

**Primera tarea de la siguiente sesión:** `status` ya validado en hardware (16/16 FULL OFF) y nueve pruebas unitarias ejecutadas en Python 3.6 (9/9, OK). La siguiente etapa es diseñar y probar la simulación independiente del brazo de seis ejes, sin habilitar salidas físicas ni conectar la alimentación de los motores. No instalar requirements.txt sobre Python 3.6.

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
- [ ] Implementar modo de prueba sin actuadores (dry-run) y armar/desarmar explícito.
- [ ] Diseñar límites de velocidad, aceleración, watchdog y gestión de pérdida de conexión.
- [ ] Ejecutar pruebas unitarias y de simulación en un entorno compatible (Mac).
- [ ] Solo después, estudiar pines I2C y compatibilidad PCA9685 para Jetson Nano 2GB.

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
- [ ] Probar comandos manuales/joystick y visualización en simulación.
- [ ] Añadir reconocimiento de gestos mediante una arquitectura compatible con los recursos.
- [ ] Introducir agente que genere propuestas de movimiento, sometidas a autorización y límites.
- [ ] Habilitar operaciones autónomas únicamente con supervisión y seguridad física verificadas.

## 12. Cómo reanudar en otra sesión sin perder el contexto

**En un nuevo chat o sesión de soporte, aportar:**

> Estamos trabajando en Antonio-Richaud/Brazo-robot, rama feat/jetson-nano-physical-ai. La Jetson Nano 2GB ya tiene JetPack 4.6.1, Ubuntu 18.04.6, L4T R32.7.1, Python 3.6.9, CUDA 10.2.300, TensorRT Python 8.2.1.8, OpenCV 4.1.1 y el venv ~/robot-lab/.venv-jetson con pip 21.3.1; SSH funciona en antonio@jetson-nano.local. El repo está en ~/robot-lab/Brazo-robot. Leer docs/06-bitacora-instalacion-jetson-nano.md, docs/07-estado-y-continuidad-del-proyecto.md y docs/08-jetson-pca9685-i2c-pruebas.md. La D435i no se ha conectado; el PCA9685 SÍ se ha conectado por I2C 0x40 a 3.3 V (OE alto), pero no se han movido servos, el backend actual necesita Python moderno y no debe instalarse sobre Python 3.6. Continuar **un paso a la vez**, solicitando salidas de comandos antes de proceder; mantener main intacta.

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

Este documento refleja lo confirmado hasta el 26-10-2026; versiones, IP, servicios y hardware deben volverse a consultar si transcurre tiempo o se cambia la instalación.
