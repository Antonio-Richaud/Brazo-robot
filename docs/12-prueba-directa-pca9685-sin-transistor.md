# Prueba directa Jetson → PCA9685 sin 2N2222 (solo supervisada)

**Estado:** ruta experimental por etapas. No existe todavía movimiento físico validado.
**Motivo de cambio:** el usuario propone enviar señales directamente por I²C y prescindir del circuito adicional para la **primera prueba manual**. Se adopta para la prueba individual supervisada; el circuito 2N2222 e interlock permanece como **mejora pendiente para operación permanente o autónoma**, no como requisito de la primera prueba.

## 1. Qué podemos y qué no podemos hacer

- **Sí:** la Jetson Nano 2GB controla por I²C al PCA9685, dispositivo `/dev/i2c-1` dirección `0x40`, con `PRE_SCALE=0x79` (50 Hz nominal). Se pueden programar los registros de un canal sin un transistor externo.
- **Hoy no habrá movimiento:** la placa tiene `OE` conectado a 3.3 V fijos desde J6 pin 17 y `FULL OFF 16/16`. Ambas barreras inhiben PWM.
- **No:** un valor de ángulo o un pulso de 1500 µs **NO demuestra posición física actual** de un SG90 acoplado. La primera habilitación podría producir movimiento abrupto, incluso con un cambio pequeño de pulso.
- **No:** el STOP que corta AC de la fuente de servos y la separación de alimentaciones **no son un watchdog de hardware**. Al apagar la Jetson se pierden los 3.3 V de OE; siempre mantener STOP activado antes de apagar/reiniciar.

Documentación base: `docs/01-hardware-y-conexiones.md`, `docs/08-jetson-pca9685-i2c-pruebas.md`, `docs/10-seguridad-fuente-servos-5v-10a.md`.

## 2. Primera prueba en el dispositivo (sin movimiento)

Se habilita de forma muy limitada la opción `stage-garra-1500` en `jetson/pca9685_safe.py`.

**Condiciones físicas antes de ejecutarla:**
1. STOP de servos **activado**; confirmar que V+ está cortado.
2. Jetson alimentada con su eliminador independiente.
3. OE continúa conectado al pin físico 17 de 3.3 V de Jetson. **No modificar ningún cable**.
4. El brazo debe permanecer apoyado y fuera del alcance de personas.

Ejecutar desde el directorio del repositorio en la Jetson:

```bash
python3 jetson/pca9685_safe.py status
python3 jetson/pca9685_safe.py stage-garra-1500 --confirm-stop-oe
python3 jetson/pca9685_safe.py status
```

**Qué hace realmente el comando:**
- Valida `MODE1` activo y `MODE2=0x04`, `PRE_SCALE=0x79`, y `FULL OFF 16/16` antes de escribir.
- Calcula un pulso de referencia de **1500 µs** para **canal 5 / garra** y escribe los cuatro registros LED5 con el bit `FULL OFF` intacto.
- Comprueba lectura del registro de `FULL OFF` del canal 5 y confirma que **los 16 siguen deshabilitados**.
- No accede a Jetson.GPIO, no baja OE, no habilita PWM, no mueve la garra, no ordena `Home`, no cambia posiciones de otros canales. El pulso de referencia **no es todavía una calibración**.
- Si encuentra una condición incorrecta, sale con error e intenta restaurar `FULL OFF`; si falla el bus, el STOP físico sigue siendo la barrera esencial.

**Salida esperada**: `GARRA_STAGE_OK`, `SIN MOVIMIENTO`, `Canales FULL OFF: 16/16`, `TODOS DESHABILITADOS: SI`.

Esto sí son **escrituras reales de registros por I²C** en la Jetson, pero **no es señal PWM en el conector del servo**, porque OE y FULL OFF permanecen en inhibición.

## 3. Arquitectura para el posterior primer movimiento SIN añadir transistor

Posible ruta *únicamente supervisada*, después de la prueba anterior y nueva revisión del montaje:

- Usar un GPIO de salida de 3.3 V de J6 **que se haya identificado oficialmente y verificado libre** para gobernar directamente la entrada OE de la placa PCA9685; su nivel HIGH inhibe salidas y LOW las permite (según registros).
- La conexión directa OE → **J6 pin 17, 3.3 V fijo** tiene que retirarse **con Jetson y fuente completamente apagadas y sin energía residual** antes de conectarla a ese GPIO. **NUNCA unir una salida digital que pueda ir LOW con OE todavía conectado a la fuente 3.3 V fija.**
- El GPIO deberá fijarse en HIGH **antes** de rearmar potencia; no poner energía a V+ durante boot, reset o caída del proceso. En placas tipo Adafruit OE tiene pull-down de fábrica: si el GPIO está flotando o Linux se reinicia, OE puede caer a LOW y **permitir señales PWM imprevistas**.
- El test físico exige como mínimo 15 canales `FULL OFF`, un único canal 5 programado, comprobación de posición inicial, pulso de primer contacto calibrado según mecanismo real, límites mecánicos y paro accesible.
- El controlador para movimiento todavía **NO está implementado**. Antes se deberá preparar y probar el programa de control en banco con mock de bus/GPIO, temporizador de duración corta, fallo bloqueado, cierre a FULL OFF y un plan operativo que mantenga STOP activado ante cualquier error.
- En ausencia de hardware independiente para vigilar OE, la pérdida de control del proceso/OS **podría dejar la salida habilitada**. Por ello no está permitida la operación desatendida ni rutinas completas ni automatización. El STOP exige al operador presente para detener energía.

**Importante:** conducir OE con GPIO directamente es una posibilidad eléctrica para una prueba de laboratorio de duración breve, **no equivale a un sistema fail-safe**. Se prioriza no modificar cables hasta concluir programación enmascarada y pruebas previas. Si no se puede garantizar la mecánica segura de la garra montada, no se inicia la prueba de movimiento.

## 4. Requisitos de aprobación del primer pulso físico

- [ ] Comando `stage-garra-1500` confirmado en Jetson real (el paso 2 de este documento).
- [ ] Conexión GPIO→OE seleccionada y verificada para el header J6 de Jetson Nano 2GB, sin cortos con pin17.
- [ ] Programa físico de un canal probado con bus simulado y manejo de fallo/timeout.
- [ ] Brazo y garra sin objetos, seguros ante caída o pellizcos; recorrido/dirección/pulso inicial revisados.
- [ ] STOP físico accionable inmediatamente; V+ no se habilita hasta que Jetson haya inicializado y confirmado inhibición de señales.
- [ ] Operador siempre presente; sin retorno automático a Home y sin comandos globales.
- [ ] Apagado posterior: inhibir salidas, accionar STOP, apagar Jetson.

**Por ahora, el paso 2 es el único autorizado.** La ruta 2N2222 de `docs/11-plan-habilitacion-fisica-2n2222.md` se conserva sin implementarla, para un diseño posterior de supervisión más robusto.

## 5. Referencias

- [PCA9685 - NXP (datasheet, control OE y registro FULL OFF)](https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf).
- [Adafruit PCA9685 - Pinouts (OE pulled LOW por defecto)](https://learn.adafruit.com/16-channel-pwm-servo-driver/pinouts).
- [Jetson Nano 2GB developer kit user guide - J6 / GPIO 3.3 V](https://developer.nvidia.com/embedded/learn/jetson-nano-2gb-devkit-user-guide).


## 6. Estado real detectado en nuevo arranque: MODE1 SLEEP y prescale default (2 de noviembre de 2026)

El usuario ejecuto desde Mac `python3 jetson/pca9685_safe.py disable-all && python3 jetson/pca9685_safe.py status` en Jetson; **salida reportada real**: `MODE1=0x11` (SLEEP), `MODE2=0x04`, `PRE_SCALE=0x1e` (~197 Hz con oscilador nominal) y `FULL OFF 16/16` despues de aplicar `disable-all` y de repetir `status`. El usuario indico mas tarde que encendio la fuente de servos; **no se ha autorizado ni ejecutado movimiento**.

En esa configuracion el chip no esta despierto para generar el pulso de servo; ademas `OE` sigue unido fisicamente a 3.3 V y FULL OFF en todos los canales, por lo que **ningun comando de movimiento desde Jetson puede mover ahora los servos**. NXP especifica que PRE_SCALE solo se escribe con MODE1.SLEEP=1. La frecuencia objetivo sera ~50 Hz, `PRE_SCALE=0x79`, `MODE1=0x01`, manteniendo FULL OFF y OE HIGH.

**Unico paso inmediato:** Accionar STOP para cortar V+ de servos antes de configurar frecuencia, mantener la Jetson encendida y OE a 3.3 V, ejecutar desde Mac:

```bash
ssh -T -o ConnectTimeout=10 antonio@jetson-nano.local '
set -e
cd "$HOME/robot-lab/Brazo-robot"
python3 jetson/pca9685_safe.py disable-all
i2cset -y 1 0x40 0x00 0x11 b
i2cset -y 1 0x40 0xFE 0x79 b
i2cset -y 1 0x40 0x00 0x01 b
sleep 0.02
python3 jetson/pca9685_safe.py status
'
```

**Criterio de exito:** `MODE1: 0x01`, `MODE2: 0x04`, `PRE_SCALE: 0x79`, `FULL OFF 16/16`, `TODOS DESHABILITADOS: SI`. Si falla, conservar STOP y no mover. Esta secuencia **NO habilita PWM y NO mueve servos**. No conectar OE a GND ni a un GPIO mientras sigue unido directamente al pin 17 de 3.3 V.

**Siguiente fase:** probar el comando `stage-garra-1500` con STOP activo y OE HIGH despues de actualizar la rama; despues abordar el pin OE y calibracion mecanica antes del primer movimiento fisico. No ejecutar rutinas completas Home/Saludo/Rutina. Requiere supervision, y sin interlock de hardware no es un sistema fail-safe para operacion automatica.
