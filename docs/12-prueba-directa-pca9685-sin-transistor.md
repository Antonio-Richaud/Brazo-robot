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

## 3. Arquitectura experimental corregida: SOLO I2C, sin GPIO ni 2N2222

**Decisión tras comprobar documentación de hardware de NVIDIA:** No usar un GPIO de J6 conectado directamente a `OE` de la placa tipo Adafruit. El header de Jetson Nano 2GB utiliza traductores TXB0108 con baja capacidad de carga DC y NVIDIA recomienda que eventuales resistencias de pull-up/pull-down en estas señales superen **50 kΩ**. La placa PCA9685 tipo Adafruit tiene OE **pulled LOW por defecto** y el valor exacto de su resistor en este clon no está certificado. Un GPIO directo podría no alcanzar niveles lógicos estables. La propuesta previa de GPIO directo queda **DESCARTADA para esta prueba**.

**Alternativa para laboratorio supervisado sin circuito adicional:** retirar completamente el conductor `OE→J6 pin17 (3.3 V fijo)` *solo con ambos equipos apagados y la fuente sin tensión*, dejar la entrada OE de la placa sin conexión externa si y solo si la propia placa demuestra un pull-down efectivo con medida `OE≈0 V` cuando Jetson vuelva a encender. Así el PCA9685 queda con **salidas globalmente permitidas** por OE LOW, pero conservamos los **16 canales FULL OFF** por registro hasta armar uno manualmente desde I2C.

**Límites importantes:**
- Este método NO es fail-safe: pérdida de software, reinicio o bus I2C pueden dejar la salida habilitada. No apropiado para trabajo autónomo ni para ejecutar rutinas completas.
- Todos los arranques/reinicios se hacen con **STOP físico ACTIVADO** hasta comprobar `FULL OFF 16/16` y frecuencia ≈50 Hz. La parada física corta AC de la fuente del servo, no garantiza tiempo de descarga instantáneo.
- La alimentación de servos **nunca** se activa durante manipulación de cables, limpieza o apagado de Jetson.
- `OE` NO debe quedar conectado simultáneamente a J6 pin17 y otro GPIO/GND. No unir nunca 3.3 V fijo y GND.
- `OE≈0 V` se mide con multímetro en el pin OE del PCA9685 respecto al GND común, con **STOP activo**, sin tocar contactos de AC. Si no se observa LOW estable, detenerse y considerar interlock/buffer.
- La primera señal tendrá 1500 μs por **250 ms** solo en canal5; los otros 15 permanecen FULL OFF. **No se sabe la posición mecánica real**; la garra puede saltar a un ángulo nuevo y debe estar despejada.

### Código ya implementado en la rama

`jetson/garra_pulso_laboratorio.py` ofrece dos acciones deliberadamente separadas:

1. `preflight` — con **STOP activado y antes de alimentar servos**: fuerza FULL OFF 16/16, configura/restaura 50 Hz si es necesario, programa canal5 con pulso de 1500 μs **todavía en FULL OFF**; verifica registros.
2. `pulse --confirm-oe-low --confirm-stop-ready` — SOLO después de que una persona confirme OE≈0 V, zona libre y STOP accesible, y tras energizar la fuente: inhibe todo, revalida frecuencia, habilita **solo canal 5 durante 250 ms** y ejecuta FULL OFF global en `finally`. No repite, no retorna a Home, ni afecta los demás canales.

**Advertencia:** `finally` no puede recuperar un sistema congelado ni garantizar parada ante fallo del bus I2C. El usuario debe accionar STOP ante cualquier movimiento anormal. Los dos flags son confirmaciones humanas, **NO verificaciones eléctricas**.

## 4. Protocolo por pasos antes del primer movimiento físico

- [x] `stage-garra-1500` ejecutado y verificado en Jetson real con `MODE1=0x01`, `MODE2=0x04`, `PRE_SCALE=0x79`, `FULL OFF 16/16`.
- [x] Código de laboratorio añadido a rama para `preflight` y pulso de 250ms solo canal 5; las pruebas automáticas deben aprobar antes de ejecutarlo físicamente.
- [ ] Con STOP activado, ejecutar apagado seguro de la Jetson. Retirar únicamente el conductor `OE→J6 pin17` con ambos equipos apagados, mantener VCC/SDA/SCL/GND y los seis servos conectados.
- [ ] Arrancar la Jetson **sin fuente de servos** y ejecutar `preflight`. Medir OE≈0 V; si no cumple, detenerse.
- [ ] Confirmar la garra libre de cargas/tope, recorrido despejado, STOP físico alcanzable, operador junto a equipo.
- [ ] Solo entonces energizar V+ de servos para prueba manual breve; ejecutar `pulse` una vez y registrar observación real de movimiento.
- [ ] Tras la prueba, activar STOP antes de cualquier reinicio/apagado de Jetson y comprobar que los canales han vuelto a FULL OFF.
- [ ] No ejecutar Home, Saludo, Rutina ni encadenar pulsos de forma automática hasta calibrar individualmente el brazo.

**No saltar pasos ni extrapolar el éxito de registros a seguridad mecánica o un movimiento ya ejecutado.** La alternativa de 2N2222 + watchdog de `docs/11-plan-habilitacion-fisica-2n2222.md` se conserva para operar con habilitación global controlada y supervisión de fallos.

## 5. Referencias

- [PCA9685 - NXP (datasheet, control OE y registro FULL OFF)](https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf).
- [Adafruit PCA9685 - Pinouts (OE pulled LOW por defecto)](https://learn.adafruit.com/16-channel-pwm-servo-driver/pinouts).
- [Jetson Nano 2GB developer kit user guide - J6 / GPIO 3.3 V](https://developer.nvidia.com/embedded/learn/jetson-nano-2gb-devkit-user-guide).
- [NVIDIA: Jetson Nano 40-Pin Expansion Header GPIO Usage Considerations / TXB0108](https://files.seeedstudio.com/wiki/reComputer/Jetson_Nano_Developer_Kit_40-Pin_Expansion_Header_GPIO_Usage_Considerations.pdf).


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

**Siguiente fase (actualizada):** `stage-garra-1500` ya comprobado; seguir la ruta I2C directa de secciones 3 y 4, primero apagado seguro y comprobacion de OE, y despues calibracion mecanica antes de primer movimiento fisico. No ejecutar rutinas completas Home/Saludo/Rutina. Requiere supervision, y sin interlock de hardware no es un sistema fail-safe para operacion automatica.


## 7. Paso 12.1 comprobado: PCA9685 reconfigurado a 50 Hz (2 de noviembre de 2026)

El usuario compartio la salida real del comando ejecutado por SSH en la Jetson:

```text
FULL OFF aplicado y comprobado en los 16 canales
MODE1: 0x11
MODE2: 0x04
PRE_SCALE: 0x1e
Canales FULL OFF: 16/16
TODOS DESHABILITADOS: SI

[i2cset MODE1 0x11; PRE_SCALE 0x79; MODE1 0x01; sleep 0.02]

MODE1: 0x01
MODE2: 0x04
PRE_SCALE: 0x79
Canales FULL OFF: 16/16
TODOS DESHABILITADOS: SI
```

**Interpretacion:** se escribieron y verificaron exitosamente los registros del PCA9685 para salir de SLEEP y fijar el divisor nominal de ~50 Hz. Los 16 canales permanecieron en FULL OFF despues de modificar frecuencia. Estos datos son lecturas de registros, no medicion instrumental de frecuencia PWM ni confirmacion de estado electrico de OE, que solo se valido antes por el usuario.

**Paso 12.2 COMPLETADO:** `stage-garra-1500 --confirm-stop-oe` ya se ejecuto en Jetson con FULL OFF 16/16. Para siguiente hito aplicar plan actualizado de secciones 3 y 4; nunca conectar OE a GND con 3.3 V fijo presente.

**Alcance:** ningun servo ha sido movido. No ejecutar Home/Saludo/Rutina aun con los seis acoplados y sin calibrar.


## 8. Bitacora y ultimo paso confirmado (2 de noviembre de 2026)

El usuario confirmo con transcripcion de SSH que `git checkout -b feat/jetson-oe-interlock-20261031 --track origin/feat/jetson-oe-interlock-20261031` funciono en la Jetson. El comando `git status -sb` devolvio `## feat/jetson-oe-interlock-20261031...origin/feat/jetson-oe-interlock-20261031`. No repetir el `checkout -b` porque la rama local ya existe.

El ultimo texto de terminal del Mac termina en `quote>`; esto indica una **comilla de shell sin cerrar**, no fallo de I2C. Salir con `Control+C` y recuperar el prompt `%` antes de continuar. `stage-garra-1500` ya fue ejecutado y confirmado posteriormente; ver bitacora y solo se puede ejecutar tras confirmar STOP y OE fisicos.

El registro paso a paso y estado pendiente se conserva en [13-bitacora-pruebas-jetson-pca9685.md](13-bitacora-pruebas-jetson-pca9685.md).
