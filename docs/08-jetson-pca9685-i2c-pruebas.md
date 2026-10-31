# Jetson Nano 2GB ↔ PCA9685: instalación I²C y pruebas sin motores

**Actualizado:** 30 de octubre de 2026  
**Estado:** comunicación I²C, escritura segura `disable-all`, lectura `status` (16/16 canales FULL OFF) y nueve pruebas unitarias comprobadas en la Jetson real; no se ha energizado la fuente de servos ni probado movimiento.  
**Rama:** feat/jetson-nano-physical-ai  
**Siguiente documento:** [07-estado-y-continuidad-del-proyecto.md](07-estado-y-continuidad-del-proyecto.md).

## 1. Objetivo y restricciones

Conectar la NVIDIA Jetson Nano **2GB original** al PCA9685 de forma independiente del ESP32 para explorar control físico directo del brazo, empezando por confirmar la comunicación a 3.3 V **sin** alimentar los motores.

Reglas obligatorias para esta fase:

- Fuente conmutada de 5 V / 10 A de servos **apagada y desconectada de V+**.
- Servos sin alimentación.
- Pin **OE del PCA9685 conectado a 3.3 V**, nivel alto que inhibe las salidas.
- No retirar OE, no probar mover motores, no aplicar 5 V a VCC/SDA/SCL de la Jetson.
- No usar Home ni comandos de movimiento durante la detección.
- El bloqueo lógico por I²C **no sustituye un interruptor de corte físico de potencia**.
- No realizar modificaciones de cableado mientras la Jetson esté alimentada.

## 2. Cableado comprobado en esta fase

Conector **J6** de 40 pines de la Jetson Nano 2GB; numeración física, no numeración de GPIO del SoC.

| Jetson J6 | PCA9685 | Descripción |
|---|---|---|
| Pin físico 1, 3.3 V | VCC | Lógica del PCA9685 |
| Pin físico 3, SDA | SDA | Datos I²C |
| Pin físico 5, SCL | SCL | Reloj I²C |
| Pin físico 6, GND | GND | Referencia común |
| Pin físico 17, 3.3 V | OE | Nivel alto para inhibir las salidas |

La conexión OE a J6 pin 17 fue realizada por el usuario y la Jetson se reinició después. No se hizo medición eléctrica del nivel en OE con multímetro o analizador lógico; **no afirmar que el estado eléctrico esté medido solo por leer I²C**.

La dirección utilizada es **0x40** en **/dev/i2c-1**. La línea V+ del PCA9685 y el conector de potencia de los servos deben permanecer sin alimentar durante todo el procedimiento.

## 3. Buses y permisos detectados

La Jetson mostró estos nodos:

~~~text
/dev/i2c-0
/dev/i2c-1
/dev/i2c-2
/dev/i2c-3
/dev/i2c-4
/dev/i2c-5
/dev/i2c-6
~~~

Adaptadores:

~~~text
i2c-0: 7000c000.i2c
i2c-1: 7000c400.i2c
i2c-2: 7000c500.i2c
i2c-3: 7000c700.i2c
i2c-4: 7000d000.i2c
i2c-5: 7000d100.i2c
i2c-6: Tegra I2C adapter
~~~

Los nodos eran crw-rw---- root:i2c y el usuario antonio ya pertenecía al grupo i2c. El ejecutable i2cdetect estaba instalado en /usr/sbin/i2cdetect. No fue necesario instalar paquetes ni elevar privilegios para las lecturas.

## 4. Diagnóstico paso a paso efectuado

### 4.1 Detectar dirección

La exploración global con i2cdetect -y 1 devolvió un aviso del adaptador:

~~~text
Warning: Can't use SMBus Quick Write command, will skip some addresses
~~~

Se resolvió la limitación de la prueba con una lectura SMBus sobre la única dirección esperada:

~~~bash
i2cdetect -r -y 1 0x40 0x40
~~~

**Resultado comprobado:** la tabla presentó 40 en la línea 40. Tras conectar OE a 3.3 V y reiniciar la Jetson, la dirección 0x40 **seguía apareciendo**.

### 4.2 Leer la configuración inicial

~~~bash
i2cget -y 1 0x40 0x00 b   # MODE1
i2cget -y 1 0x40 0x01 b   # MODE2
i2cget -y 1 0x40 0xFE b   # PRE_SCALE
~~~

**Resultados iniciales:** MODE1 = 0x11 (SLEEP activado), MODE2 = 0x04 (salidas push-pull, OUTNE[1:0]=00), PRE_SCALE = 0x1E (unos 197 Hz nominales).

### 4.3 Ajustar frecuencia nominal a ~50 Hz

Como MODE1=0x11 y SLEEP ya estaba activado, se hizo:

~~~bash
i2cset -y 1 0x40 0xFE 0x79 b
i2cget -y 1 0x40 0xFE b
i2cget -y 1 0x40 0x00 b
~~~

**Resultado:** PRE_SCALE = 0x79 y MODE1 = 0x11.

Usando el oscilador nominal de 25 MHz:
f_PWM = 25,000,000 / (4096 × (121 + 1)) = aproximadamente 50.03 Hz.
La frecuencia física exacta depende de la tolerancia del oscilador; no se ha medido con un instrumento.

### 4.4 Desactivar las 16 salidas

Se escribió el bit FULL OFF en el registro global, que afecta a los registros individuales:

~~~bash
i2cset -y 1 0x40 0xFD 0x10 b  # ALL_LED_OFF_H (registro solo escritura)
i2cget -y 1 0x40 0x09 b        # LED0_OFF_H
i2cget -y 1 0x40 0x45 b        # LED15_OFF_H
~~~

**Resultado:** ambos registros individuales devolvieron 0x10. FULL OFF es el bit 4 de cada LEDn_OFF_H. El registro global 0xFD se comprueba leyendo los registros individuales, no leyendo 0xFD.

### 4.5 Activar oscilador conservando OFF

~~~bash
i2cset -y 1 0x40 0x00 0x01 b  # MODE1: SLEEP=0
sleep 1
i2cget -y 1 0x40 0x00 b
i2cget -y 1 0x40 0x09 b
i2cget -y 1 0x40 0x45 b
~~~

**Resultado:** MODE1=0x01; canal 0 OFF_H=0x10; canal 15 OFF_H=0x10.

### 4.6 Programar canal 0 con salida desactivada

Se efectuó la prueba con los motores sin alimentación y OE en alto:

~~~bash
i2cset -y 1 0x40 0x06 0x00 b  # LED0_ON_L
i2cset -y 1 0x40 0x07 0x00 b  # LED0_ON_H
i2cset -y 1 0x40 0x08 0x33 b  # LED0_OFF_L
i2cset -y 1 0x40 0x09 0x11 b  # LED0_OFF_H: cuenta alta=1 y FULL OFF=1
~~~

**Última lectura comprobada por usuario:**

~~~text
0x08: 0x33
0x09: 0x11
0x00: 0x01
~~~

Significado: 0x133 = **307 cuentas PWM**, correspondientes a ~1,498 microsegundos nominales a 50.03 Hz. El bit FULL OFF sigue a 1, por lo que el canal permanece deshabilitado. **No se ha generado un pulso físico ni movido un motor**.

## 5. Herramienta de inspección segura incluida en el repositorio

La rama Jetson incorpora:

- [jetson/pca9685_safe.py](../jetson/pca9685_safe.py): compatible con Python 3.6; solo consulta estado o aplica FULL OFF.
- [jetson/tests/test_pca9685_safe.py](../jetson/tests/test_pca9685_safe.py): nueve pruebas de unidad con transporte I²C simulado.

Utiliza las utilidades i2cget/i2cset ya instaladas. No necesita pip, ROS ni bibliotecas nuevas.

**Para consultar sin escribir registros:**

~~~bash
cd ~/robot-lab/Brazo-robot
git pull --ff-only origin feat/jetson-nano-physical-ai
python3 jetson/pca9685_safe.py status
~~~

El comando lee MODE1, MODE2, PRE_SCALE y los 16 registros LEDn_OFF_H. Si todos tienen el bit FULL OFF, muestra:

~~~text
Canales FULL OFF: 16/16
TODOS DESHABILITADOS: SI
~~~

El software no puede leer el estado del pin OE: verificar siempre su cableado físico.

**Solo cuando se necesite escribir FULL OFF de manera explícita:**

~~~bash
python3 jetson/pca9685_safe.py disable-all
~~~

La acción disable-all escribe 0x10 en ALL_LED_OFF_H y verifica FULL OFF en los 16 canales. No habilita ninguna salida. Este comando **no es** un paro de emergencia físico.

El módulo contiene una función interna stage_disabled_pulse para preparar cuentas conservando FULL OFF; **no está expuesta en la línea de comandos** y no existe acción arm/enable/set_servo_angle. El transporte i2c-tools es adecuado para diagnóstico, **no** es un lazo determinista de control de movimiento.

Pruebas sin hardware (por ejemplo en la Jetson):

~~~bash
cd ~/robot-lab/Brazo-robot
python3 -m unittest discover -s jetson/tests -v
~~~

**Verificación real efectuada el 30-10-2026** desde la Jetson Nano 2GB, tras `git pull --ff-only origin feat/jetson-nano-physical-ai`:

~~~bash
python3 jetson/pca9685_safe.py status
~~~

Salida reportada:

~~~text
=== PCA9685 /dev/i2c-1 / 0x40 ===
MODE1: 0x01
MODE2: 0x04
PRE_SCALE: 0x79
Canales FULL OFF: 16/16
TODOS DESHABILITADOS: SI
OE: NO verificable por I2C; mantener OE -> 3.3 V
IMPORTANTE: FULL OFF no reemplaza un corte fisico de potencia
~~~

**Conclusión:** el programa de inspección funciona y lee los 16 canales desde la Jetson. El estado del pin OE no se ha medido eléctricamente. La acción `disable-all` del programa **ya se ejecutó con éxito en la Jetson real**, confirmando FULL OFF en los 16 canales. Las nueve pruebas unitarias **se ejecutaron después con éxito** sobre Python 3.6 de la Jetson: 9/9 aprobadas en 0.003 s (`OK`). Ninguna de ellas energiza motores o modifica el PCA9685 real.

### 5.1. Ejecución de las nueve pruebas en la Jetson Nano real

El usuario ejecutó desde la Jetson, tras actualizar al commit `3bf41cb`:

~~~bash
cd ~/robot-lab/Brazo-robot
python3 -m unittest discover -s jetson/tests -v
~~~

Resultado real:

~~~text
test_disable_all_fails_if_hardware_does_not_accept_command ... ok
test_disable_all_sets_full_off_on_each_channel ... ok
test_no_enable_or_arm_api ... ok
test_no_stage_if_any_channel_is_enabled ... ok
test_no_stage_out_of_range ... ok
test_no_stage_with_wrong_prescale ... ok
test_stage_disabled_1500us_channel_zero ... ok
test_status_is_read_only ... ok
test_transport_restricts_bus_and_address ... ok

Ran 9 tests in 0.003s

OK
~~~

**Alcance:** se validó compatibilidad y lógica con un bus simulado en Python 3.6 de la Jetson. Esto **no valida eléctricamente OE, V+ ni el movimiento físico de un servo**. La acción `disable-all` contra el hardware real **se verificó después con éxito**.

### 5.2. Validación del comando `disable-all` contra el PCA9685 real

El usuario ejecutó en la Jetson (después de actualizar al commit `05f0e0a`):

~~~bash
python3 jetson/pca9685_safe.py disable-all
~~~

Salida observada:

~~~text
FULL OFF aplicado y comprobado en los 16 canales
=== PCA9685 /dev/i2c-1 / 0x40 ===
MODE1: 0x01
MODE2: 0x04
PRE_SCALE: 0x79
Canales FULL OFF: 16/16
TODOS DESHABILITADOS: SI
OE: NO verificable por I2C; mantener OE -> 3.3 V
IMPORTANTE: FULL OFF no reemplaza un corte fisico de potencia
~~~

**Confirmado:** el dispositivo real aceptó la escritura global ALL_LED_OFF_H y el programa verificó FULL OFF individual en los 16 canales. No se ha medido nivel físico de OE con instrumental ni se ha probado paro de emergencia. Ningún motor alimentado o movido.

## 6. Próximas pruebas y requisitos antes de mover el brazo

1. [Completado] Sincronizar la rama en la Jetson, ejecutar status (solo lectura) y verificar los 16 canales.
2. [Completado] Probar la batería de nueve unidades con Python 3.6 de JetPack (9/9, `OK`, 0.003 s).
3. [Completado] Ejecutar `python3 jetson/pca9685_safe.py disable-all` en la Jetson real; FULL OFF 16/16, MODE1=0x01, MODE2=0x04, PRE_SCALE=0x79.
4. [Código añadido, pendiente de pruebas en Jetson] Simulador sin hardware con DISARMED inicial, validación de límites, velocidades y watchdog cooperativo: [09-jetson-simulacion-seis-servos.md](09-jetson-simulacion-seis-servos.md). La seguridad de hardware y el corte físico siguen pendientes.
5. Antes de alimentar servos: verificar tensión real de VCC/V+, polaridad de la fuente, tierra común, orden de los terminales de cada servo y dirección de sus conectores.
6. Instalar y probar un mecanismo físico para cortar la alimentación de los servos (emergencia). OE es una protección de señal, no un corte de potencia.
7. Habilitar solo un servo a la vez, sin carga, y calibrar pulsos individuales con tolerancia mecánica; nunca suponer que 1500 µs corresponde al centro mecánico seguro del brazo armado.
8. Incorporar control con seguridad por defecto, telemetría y gemelo digital y pruebas automatizadas antes de autonomía.

**No hacer los puntos 5–8 sin diseño y revisión del cableado.**

## 7. Hojas de datos y referencias

- NXP PCA9685, hoja de datos: https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf
- [01-hardware-y-conexiones.md](01-hardware-y-conexiones.md): ESP32 y tabla de articulaciones.
- [06-bitacora-instalacion-jetson-nano.md](06-bitacora-instalacion-jetson-nano.md): instalación Ubuntu/JetPack, entornos, red y errores previos.
- [07-estado-y-continuidad-del-proyecto.md](07-estado-y-continuidad-del-proyecto.md): objetivos y decisiones de arquitectura.
