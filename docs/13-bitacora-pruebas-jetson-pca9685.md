# Bitácora de pruebas físicas - Jetson Nano 2GB / PCA9685

**Fecha de actualización:** 2 de noviembre de 2026.
**Rama de trabajo:** `feat/jetson-oe-interlock-20261031`.
**Pull request:** [#7](https://github.com/Antonio-Richaud/Brazo-robot/pull/7) (borrador).
**Política:** registrar por separado **reportes del usuario**, **resultados de comando comprobados por salida copiada** y **acciones pendientes**. No reportar movimiento como hecho hasta tener observación física del usuario.

## Estado fijo del montaje reportado

- Jetson Nano 2GB, Ubuntu 18.04 / JetPack 4.6.1, Python 3.6; acceso por SSH `antonio@jetson-nano.local`.
- PCA9685 en `/dev/i2c-1`, dirección `0x40`.
- Control lógico J6: pin 1 a VCC 3.3 V, pin 3 SDA, pin 5 SCL, pin 6 GND, **pin 17 (3.3 V fijo) a OE**.
- Fuente de servos 5 V / 10 A separada, con STOP físico que, según usuario, corta **la entrada AC** de dicha fuente, no la Jetson.
- Brazo ensamblado: 3 MG995 (canales 0-2), 3 SG90 (canales 3-5), garra: canal 5.
- **No existe aún movimiento físico comprobado desde la Jetson**, ni calibración real de ángulos.
- La fuente puede haberse energizado durante las pruebas: **el estado actual del STOP no se puede inferir de un log**. Confirmarlo físicamente antes de cada paso.

## Registro cronológico de pruebas verificadas

| Paso | Evidencia entregada | Resultado |
|---|---|---|
| I2C y bloqueo inicial | Salida SSH de `python3 jetson/pca9685_safe.py disable-all` seguida de `status` | PCA9685 accesible; `MODE1=0x11`, `MODE2=0x04`, `PRE_SCALE=0x1E`, `FULL OFF 16/16`; frecuencia aún no apta para servos |
| Restauración 50 Hz | SSH con `i2cset` `MODE1 0x11` → `PRE_SCALE 0x79` → `MODE1 0x01`; lectura posterior | **Correcto:** `MODE1=0x01`, `MODE2=0x04`, `PRE_SCALE=0x79`, `FULL OFF 16/16` |
| Cambio de rama en Jetson (intento 1) | `git switch` | No disponible en Git instalado en Jetson. No se ejecutó `stage-garra-1500` |
| Cambio de rama en Jetson (intento 2) | `git checkout -b feat/jetson-oe-interlock-20261031 --track origin/feat/jetson-oe-interlock-20261031`; `git status -sb` | **Correcto:** rama creada, configurada para seguimiento remoto, `## feat/jetson-oe-interlock-20261031...origin/feat/jetson-oe-interlock-20261031` sin cambios listados |
| Última salida de terminal Mac | Después de copiar una transcripción con el prompt duplicado: `quote>` | **No es un error de la Jetson.** La shell de Mac está esperando cierre de comilla. Salir con `Control+C`; no ejecutar `git checkout -b` otra vez |
| Prueba de registros de garra (2 de noviembre 2026) | `stage-garra-1500 --confirm-stop-oe` más `status` ejecutados en Jetson | **CORRECTO:** `GARRA_STAGE_OK: canal 5, 1500 us (307 cuentas)`, `FULL OFF 16/16`, `MODE1=0x01`, `MODE2=0x04`, `PRE_SCALE=0x79`. No se habilitaron salidas ni se confirmó movimiento físico |

## Próximo paso pendiente: prueba I2C de garra enmascarada

**PRECONDICIONES OBLIGATORIAS, confirmar manualmente:** STOP físico activado; V+ sin energía; Jetson encendida; OE físicamente unido al pin 17 de 3.3 V; zona despejada.

1. En Mac, si muestra `quote>`, presionar `Control+C` hasta recuperar prompt normal `%`.
2. Ejecutar:

```bash
ssh -T -o ConnectTimeout=10 antonio@jetson-nano.local 'cd "$HOME/robot-lab/Brazo-robot" && python3 jetson/pca9685_safe.py stage-garra-1500 --confirm-stop-oe && python3 jetson/pca9685_safe.py status'
```

3. Verificar en la salida `GARRA_STAGE_OK`, `SIN MOVIMIENTO`, `FULL OFF 16/16` y `TODOS DESHABILITADOS: SI`.

**Estado del paso:** `APROBADO` el 2 de noviembre de 2026; ver evidencia verificada al final de este documento. **Movimiento físico:** pendiente.

## Prohibiciones y límites durante esta etapa

- No unir OE a GND ni a un GPIO sin antes quitar físicamente, con equipos apagados, el cable que lo mantiene a 3.3 V fijo; GPIO LOW en paralelo produciría conflicto eléctrico.
- No alimentar V+ con `OE` sin nivel medido. Para la prueba directa, solo se permite OE desconectado del pin17 si el pull-down de la placa lo mantiene estable cerca de 0 V; no poner el brazo en Home al arrancar.
- No ejecutar Saludo/Rutina sobre los seis servos montados sin calibración individual.
- El flag `--confirm-stop-oe` **no es un sensor**; únicamente indica la confirmación del operador y no puede comprobar cableado ni STOP.
- La prueba de preparación escribe registros de un pulso **enmascarado**; no emite PWM hacia servos y no supone prueba física de movimiento.
- Documentación técnica ampliada: [protocolo directo](12-prueba-directa-pca9685-sin-transistor.md) y [seguridad potencia](10-seguridad-fuente-servos-5v-10a.md).

## Criterio para marcar nuevos hitos

Incluir siempre fecha, comando exacto, salida relevante, estado del STOP/OE informado, interpretación y pendientes. No afirmar que pruebas en mocks, CI o lecturas de registros equivalen a movimiento.

## Hito validado: pulso de garra preparado sin habilitar PWM (2 de noviembre de 2026)

El usuario reporto la salida real desde su Mac de la ejecucion remota en Jetson Nano:

```text
GARRA_STAGE_OK: canal 5, 1500 us (307 cuentas)
SIN MOVIMIENTO: FULL OFF 16/16 y OE HIGH externo
MODE1: 0x01
MODE2: 0x04
PRE_SCALE: 0x79
Canales FULL OFF: 16/16
TODOS DESHABILITADOS: SI
```

Se ejecuto otro `status` al final que repitio `MODE1=0x01`, `MODE2=0x04`, `PRE_SCALE=0x79`, `FULL OFF 16/16`. No hay errores I2C en salida.

**Interpretacion:** el software preparo exitosamente la duracion de pulso de 1500 us (307 cuentas del PCA9685) sobre los registros del canal 5 de garra y mantuvo TODOS los canales inhibidos. El programa NO comprobo fisicamente OE; su mensaje 'OE HIGH externo' depende de cableado previamente reportado (pin J6 17 de 3.3 V), y el flag `--confirm-stop-oe` depende de la confirmacion del usuario. No se midio PWM con osciloscopio ni movimiento ni posicion de servo.

**Siguiente fase:** antes del movimiento real, establecer control fisico seguro de OE (hoy atado a 3.3 V constante), implementar movimiento de un solo eje en codigo con estado inicial controlado, aislamiento `FULL OFF` de canales 0-4 y 6-15, tiempo limitado, corte logico de salida y STOP de potencia accesible. Evitar que `OE` flote durante arranque, apagar primero potencia ante fallos y NO probar Home/Saludo/Rutina completos con 6 servos acoplados sin calibracion.

**Estado de hito:** APROBADO (programacion I2C enmascarada); **primer movimiento fisico:** PENDIENTE. **Estado actual del STOP:** no inferible de la salida.

## Diseño preparado para primer movimiento sin circuito adicional (2 de noviembre de 2026)

Tras comprobar el hito `GARRA_STAGE_OK`, se investigo el hardware de Jetson Nano 2GB y la placa PCA9685: los conectores GPIO de J6 usan TXB0108, que NVIDIA documenta con alta sensibilidad a pull-up/down externos. La placa tipo Adafruit mantiene `OE` pulled LOW. **Se descarta la idea de conectar OE directamente a GPIO en esta prueba** por riesgo de niveles incompatibles.

**Se agrego al repositorio** el modulo `jetson/garra_pulso_laboratorio.py` con dos comandos: `preflight` (no movimiento; FULL OFF, modo y frecuencia, canal5 enmascarado) y `pulse --confirm-oe-low --confirm-stop-ready` (250ms a 1500us solo canal5, FULL OFF global en finally). Pruebas automatizadas de mock en `jetson/tests/test_garra_pulso_laboratorio.py`. **El usuario NO ha ejecutado estos comandos aun ni ha retirado el cable OE**.

El primer movimiento real no depende de un transistor, pero requerira **con equipos apagados** retirar SOLO el jumper actual de OE a J6 pin17 3.3V; verificar con multimetro que OE queda cerca de 0 V gracias al pull-down de la placa, STOP de potencia activado durante boot/preflight, y luego operar manualmente con paro fisico accesible. No existe control fail-safe por software y no esta autorizada una rutina completa automatica.

**Referencias y procedimiento actualizados:** [docs/12-prueba-directa-pca9685-sin-transistor.md](12-prueba-directa-pca9685-sin-transistor.md). Estado: codigo en rama, hardware OE aun no modificado; primera prueba fisica PENDIENTE.


## Hito reportado: OE separado de 3.3 V (2 de noviembre de 2026)

El usuario confirmo expresamente: **«Listo 0E desconectado de 3.3 v»**. Se registra que, segun reporte del usuario, el jumper que conectaba `OE` del PCA9685 a J6 pin fisico 17 (3.3 V fijo) ya fue retirado.

**No comprobado:** estado actual de apagado de Jetson, ausencia de 5 V en V+, nivel electrico real de OE, pull-down efectivo de la placa, primer movimiento fisico o frecuencia del modulo tras reinicio. No inferir esos datos de la confirmacion de retiro de cable.

**Siguiente comprobacion unica:** dejar fuente de servos cortada mediante STOP y desconectada de AC; no conectar ninguna resistencia ni GPIO a OE; encender solo Jetson para alimentar VCC logico y medir con multimetro en voltaje DC entre `OE` (punta roja) y `GND` (punta negra) en la placa, evitando puentes accidentales. Se espera cercano a **0 V** si el pull-down de la placa es eficaz. Si no es cercano a 0 V, es fluctuante o la medicion es insegura, detenerse; no energizar la fuente de servos. Aun con OE LOW, las señales del PCA9685 podrian habilitarse segun registros, de modo que **STOP permanece activado durante todo el arranque y preflight**.

**Pendiente tras medicion confirmada:** actualizar rama en Jetson, correr `garra_pulso_laboratorio.py preflight` con STOP activo y comprobar los 16 FULL OFF; solo despues decidir prueba fisica puntual supervisada.


## Hito reportado: lectura de OE aproximadamente 0 V (2 de noviembre de 2026)

Tras las instrucciones de medir la tension entre **OE (punta roja)** y **GND (punta negra)** de la placa PCA9685 con la Jetson encendida y la fuente de servos apagada, el usuario respondio textualmente: **«0 no marca gnd»**. Se interpreta provisionalmente como **lectura de 0 V** en el multimetro, no como una prueba de continuidad ni una lectura de etiqueta GND.

**Resultado:** nivel OE cercano a 0 V **reportado por el usuario**; compatible con el pull-down de la placa tras retirar el jumper OE→3.3 V. La lectura no verifica automaticamente integridad de GND, potencia de servos, corriente, canal habilitado ni seguridad de movimiento. Si el usuario quiso decir que NO encontro referencia GND para medir, detenerse y aclarar antes de energizar V+.

**Siguiente paso:** mantener STOP activo, con V+ sin energia; Jetson encendida. Sin tocar cables ni energizar fuente, actualizar rama en Jetson con `git pull --ff-only origin feat/jetson-oe-interlock-20261031` (Git antiguo soporta pull pero no switch) y ejecutar `python3 jetson/garra_pulso_laboratorio.py preflight`. Este comando fuerza FULL OFF 16/16, configura frecuencia si es necesario y prepara pulso enmascarado del canal 5; NO habilita PWM ni mueve servos.

**Criterios:** `PREFLIGHT_OK`, `FULL OFF 16/16`; si falla, no activar potencia. El movimiento (`pulse`) permanece PENDIENTE, requiere supervision y STOP al alcance.


## Incidencia de comunicacion I2C en preflight y aclaracion sobre 2N2222 (registro: 3 de noviembre de 2026)

**Evidencia entregada por usuario:** Despues de actualizar correctamente la rama de `130d35d` a `f6b1583` con `git pull --ff-only`, la Jetson ejecuto `python3 jetson/garra_pulso_laboratorio.py preflight` y fallo en la primera escritura de `SafePCA9685.disable_all()`:

```text
subprocess.CalledProcessError: Command '['i2cset', '-y', '1', '0x40', '0xfd', '0x10', 'b']' returned non-zero exit status 1.
```

- Esta escritura pretendia establecer `ALL_LED_OFF_H[4]=1` / FULL OFF global. El script se detuvo **antes** de programar o habilitar canal 5. El segundo comando `pca9685_safe.py status` no se ejecuto porque la sesion utilizo `set -e`.
- **No puede concluirse** que los canales sigan todos deshabilitados tras este error. OE previamente fue reportado cercano a 0 V tras separar pin17 y por ello los PWM ya no cuentan con inhibicion de hardware; mantener la alimentacion 5 V de servos **cortada con STOP**.
- Retirar exclusivamente el cable `OE` no deberia impedir que el PCA9685 responda por I2C. Causas a diagnosticar: VCC logico 3.3 V/GND ausentes o flojos, SDA/SCL accidentalmente desconectados, bus o dispositivo no disponible, o error I2C transitorio. El codigo antiguo capturaba stderr en `subprocess.run` pero mostraba traceback sin el detalle de error devuelto por `i2cset`. No diagnosticar la causa exacta sin prueba.
- La finalidad del **2N2222** es gobernar OE: transistor NPN apagado deja OE en HIGH a traves de una **resistencia pull-up** de 3.3 V; encendido hunde OE a LOW para permitir salidas seleccionadas por registros. No se usa para alimentar la potencia de servos ni suministrar directamente 3.3 V, y **no reemplaza STOP**. El diseno con GPIO Jetson y TXB0108 requiere validacion de carga y un interlock/watchdog separado si se requiere fail-safe.

**Correccion de software en rama (no ejecutada aun en Jetson):** `jetson/pca9685_safe.py` transforma `subprocess.CalledProcessError` y `TimeoutExpired` en errores descriptivos que incluyen stderr del comando I2C, cubiertos por nuevas pruebas unitarias. El codigo no reintenta escrituras si el bus falla, no habilita PWM y no altera el estado fisico.

**UNICO siguiente diagnostico propuesto (con STOP activado, sin energizar V+; NO tocar cables):**

```bash
ssh -T -o ConnectTimeout=10 antonio@jetson-nano.local 'i2cget -y 1 0x40 0x00 b'
```

Lectura MODE1 sin modificar registros. Si devuelve un byte hexadecimal (`0x..`), el chip responde a **esa** lectura; si devuelve error, conservar STOP y revisar alimentacion logica/cables con equipos apagados antes de nuevas operaciones. No iniciar `pulse`, Saludo, Home o Rutina hasta recuperar control de I2C.


## Incidencia confirmada: falla de lectura MODE1 y lista de resistencias futura (3 de noviembre de 2026)

El usuario ejecuto en Jetson con SSH:

```text
i2cget -y 1 0x40 0x00 b
Error: Read failed
```

**Interpretacion:** tras el fallo previo de `i2cset 0xFD <- 0x10`, ahora tambien falla la lectura del registro MODE1 0x00. La comunicacion I2C con 0x40 no esta operativa en este momento. No puede atribuirse solo a OE ni al software nuevo; OE controla salidas PWM, no la direccion I2C. El hecho de haber manipulado recientemente el jumper OE obliga a comprobar si se aflojaron VCC, GND, SDA, SCL; tambien verificar bus/placa sin adivinar.

**Accion inmediata:** mantener STOP presionado y fuente V+ sin corriente. Con Jetson encendida y sin manipular cables, medir tension DC entre **VCC y GND del PCA9685**. Esperado aproximadamente 3.3 V. Si es 0 V o fluctua, cortar alimentacion y revisar cableado de 3.3 V y masa con todo apagado. Si es 3.3 V, revisar SDA/SCL/masa e I2C en otro paso. No ejecutar `preflight`, `pulse`, Home, Saludo o Rutina hasta resolver el I2C. No reconectar OE a 3.3 V en caliente para intentar resolverlo.

### Lista de compras PRELIMINAR del circuito con 2N2222 (no instalar aun)

| Resistencia | Cantidad sugerida | Función propuesta | Estado |
|---|---:|---|---|
| 1 kΩ | 5 | Candidata pull-up de OE a 3.3 V; verificar pull-down real y VIH | No dimensionada definitivamente |
| 4.7 kΩ | 5 | Candidata limitadora de base del 2N2222 en montaje con salida buffer adecuada | No conectar a GPIO Jetson sin verificar TXB0108 |
| 10 kΩ | 5 | Alternativa de polarización/dimensionamiento | De reserva |
| 47 kΩ | 5 | Candidata de base a masa en etapa de transistor | No dimensionada definitivamente |
| 100 kΩ | 5 | Alternativa de resistencia de base a masa (valor alto) | De reserva |

Resistencias de pelicula metalica o carbono, 1/4 W, 1% o 5% tolerancia, terminales THT. Las cantidades de 5 son reserva; **no se necesitan 5 por circuito**. Un kit surtido que incluya los cinco valores es adecuado. Especificaciones finales dependen de medir la resistencia a GND del OE de la placa y elegir la etapa de manejo. La Jetson Nano 2GB usa TXB0108 en pines no I2C: Nvidia recomienda pull-up/down externos superiores a 50 kΩ en esos pines, por lo que un transistor/carga de base directo merece un driver/buffer apropiado (o diseno alternativo), no asumir que 4.7k es compatible por si solo. Un 2N2222 **no es** un watchdog ni STOP; si se necesita fail-safe ante congelamiento de Jetson, agregar supervisor hardware independiente.

**Fuentes de dimensionamiento:** PCA9685 NXP datasheet (OE VIH >= 0.7 VDD); Adafruit PCA9685 pinout (OE pulled low by default); NVIDIA Jetson Nano 40-Pin Expansion Header GPIO Usage Considerations (TXB0108).


## Diagnostico I2C: VCC logico de 3.3 V confirmado (3 de noviembre de 2026)

Tras registrar fallo de escritura `i2cset ... 0xFD 0x10` y de lectura `i2cget -y 1 0x40 0x00 b` con `Error: Read failed`, se solicito medir tension DC en la placa PCA9685 entre VCC y GND, con Jetson encendida y fuente V+ de servos cortada por STOP.

**Resultado reportado por el usuario:** «Si tengo 3.3v». El pin VCC de la placa dispone por tanto de ~3.3 V respecto a GND segun medicion del usuario. Esto no confirma que SDA/SCL tengan continuidad, que la direccion 0x40 responda o que I2C no este retenido LOW.

**Proxima prueba (sin cableado nuevo, sin energizar V+):** escanear exclusivamente la direccion esperada 0x40 en el bus I2C-1 con `i2cdetect -y -r 1 0x40 0x40`. Si muestra `40`, hay respuesta al sondeo SMBus en esa direccion, pero no garantiza lecturas/escrituras de registros. Si muestra `--` o `Error`, no hay respuesta diagnostica suficiente; inspeccionar conexiones con equipos apagados y, por separado, medir SDA/SCL segun siguientes resultados. El escaneo I2C no escribe PWM pero genera trafico de sondeo; no realizarlo con servos energizados ni tratarlo como operacion de seguridad.

**No ejecutar** `preflight`, `pulse`, `Home`, `Saludo`, `Rutina` ni cambiar OE/3.3 V hasta recuperar I2C y confirmar FULL OFF. STOP sigue activado.


## Diagnostico 3 nov 2026: 0x40 no responde al escaneo I2C

Comando ejecutado y salida enviada por el usuario:

```text
ssh -T -o ConnectTimeout=10 antonio@jetson-nano.local 'i2cdetect -y -r 1 0x40 0x40'
40: --
```

**Interpretacion:** sondeo SMBus de solo la direccion `0x40` en `/dev/i2c-1`: no se recibio ACK. Combinado con `i2cget ... Error: Read failed` y fallo de `i2cset` ALL_LED_OFF, el PCA9685 actualmente **no se comunica** con Jetson. En contraste, usuario midio aproximadamente **3.3 V entre VCC y GND** de la placa. Esto comprueba alimentacion logica en ese punto, pero no continuidad SDA/SCL, niveles de bus ni funcionamiento interno del chip. No afirmar aun una falla definitiva del modulo.

**Siguiente paso unico recomendado (sin mover ni reconfigurar):** con STOP fisico activado, sin potencia V+ de servos, Jetson encendida, multimetro en V DC medir `SDA` contra `GND` del PCA9685 en estado de reposo, evitando puentear pines con puntas. El bus I2C necesita nivel HIGH por resistencias pull-up durante reposo, tipicamente alrededor de 3.3 V. Lectura sostenida cerca de 0 V apunta a linea retenida LOW o corto; nivel alto no garantiza continuidad I2C. Si resulta incomodo medir pines juntos, detenerse y apagar ambos equipos para inspeccionar continuidad/ubicacion fisica de cables. No permitir `pulse`, `preflight` ni fuente V+ hasta resolver.

**Conexion nominal:** Jetson J6 pin3 = SDA, pin5 = SCL, pin6 = GND, pin1 = VCC 3.3V. OE ya separado de pin17 segun reporte; dejarlo sin reconectar durante diagnostico. La advertencia SSH de intercambio de claves post-cuántico no explica el fallo I2C.


## Diagnostico I2C: SDA aparentemente correcta; falta medir SCL (3 de noviembre de 2026)

Tras solicitar la medicion de la linea SDA (punta negra GND, roja SDA) con la Jetson encendida y STOP de servos activo, el usuario respondio: **«Todo parece estar correcto»**. No facilito una lectura numerica ni confirmo expresamente haber medido SDA; se registra como **observacion cualitativa**, NO como valor verificado de SDA≈3.3 V.

La evidencia previa permanece: VCC≈3.3 V reportado; `i2cget -y 1 0x40 0x00 b` devolvio `Error: Read failed`, y `i2cdetect -y -r 1 0x40 0x40` mostro `40: --`. El modulo **aun no responde por I2C**; una linea en HIGH en reposo no demuestra continuidad ni ACK.

**Siguiente comprobacion unica**: mantener STOP activado, fuente V+ de servos desenergizada, Jetson encendida, y medir tension DC de **SCL del PCA9685 respecto a GND**, registrando cifra exacta; normal en reposo cerca de 3.3 V. Evitar puentear pines vecinos con el multimetro. Si SCL es ~3.3 V, seguir diagnosticando continuidad/orden de SDA y SCL con equipos totalmente apagados, sin afirmar que I2C funciona. No ejecutar `preflight`, `pulse`, Home ni rutinas.


## Hipotesis revisada: la retirada de OE no deshabilita I2C (3 de noviembre de 2026)

El usuario pregunta si el fallo de deteccion `0x40` pudo ocurrir por quitar el cable de `OE`. Documentacion tecnica confirmada:

- NXP PCA9685 datasheet (https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf): OE es una entrada de **habilitacion asincrona de las 16 salidas PWM**, no controla el receptor I2C, los registros ni la direccion.
- Adafruit PCA9685 pinouts (https://learn.adafruit.com/16-channel-pwm-servo-driver/pinouts): OE esta conectado a un pull-down en la placa original y es opcional; sin conexion externa mantiene salidas potencialmente habilitadas. Esto NO garantiza el comportamiento de todos los clones ni una parada segura.

**Conclusion:** quitar correctamente el jumper OE→J6 pin17 no deberia causar `i2cget Error: Read failed` ni `i2cdetect 40: --`. Que ambos hechos hayan ocurrido despues de manipular la placa justifica revisar posibles desconexiones accidentales en SDA/SCL/GND, errores de pin o cortos transitorios, pero no demuestra causalidad; VCC de 3.3 V fue reportado, sin verificar integridad I2C.

**Proximo paso de bajo riesgo:** con STOP de fuente de servos activado, sin energizar V+, y luego de que Jetson termine de reiniciarse, repetir sondeo a una sola direccion: `i2cdetect -y -r 1 0x40 0x40`. Si sigue `--`, cortar energia de ambos equipos y revisar conectores J6 1→VCC, 3→SDA, 5→SCL, 6→GND con inspeccion y continuidad sin alimentacion. No reinsertar OE a 3.3V para intentar arreglar I2C, ni habilitar la potencia mientras falle comunicacion.
