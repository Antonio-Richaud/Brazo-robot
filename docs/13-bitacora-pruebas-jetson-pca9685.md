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
- No alimentar V+ con `OE` flotante, ni poner el brazo en Home al arrancar.
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
