# Cableado correcto: Jetson Nano 2GB (J6) -> PCA9685

**Estado:** referencia para diagnostico de fallo I2C (3 de noviembre de 2026).
**Montaje real:** brazo robot con seis servos instalados; Jetson Nano 2GB, PCA9685 tipo Adafruit, alimentacion logica 3.3 V, fuente de servos independiente de 5 V/10 A, STOP fisico de alimentacion de servos. **No se ha comprobado movimiento fisico seguro.**
**Incidencia vigente:** `i2cget -y 1 0x40 0x00 b` devuelve `Error: Read failed`; `i2cdetect -y -r 1 0x40 0x40` muestra `40: --`. El usuario ha medido ~3.3 V entre VCC y GND; por tanto es necesario inspeccionar las conexiones reales SDA/SCL/GND y continuidad. No afirmar que se resolvio.

## 1. Precauciones antes de verificar el cableado

1. **Accionar STOP** para cortar la fuente de 5 V de servos y desconectar su entrada AC; evitar tocar entrada de red o bornes AC, que deben estar protegidos. Las fuentes pueden retener carga.
2. Apagar Jetson y desconectar su alimentador USB-C. Comprobar ausencia de tension en el lado de baja tension antes de mover jumpers o usar continuidad.
3. No conectar o desconectar cables con dispositivos encendidos. No utilizar ningun comando `pulse`, `preflight`, Home, Saludo o Rutina durante esta incidencia.
4. Si hay una ESP32 conectada simultaneamente al bus I2C, no mantenerla conectada; el control Jetson usa un unico maestro bajo este montaje, sin cableado multimaestro validado.
5. Identificar **pin 1 de J6 por la marca real en la placa**. Los números siguientes son **pines fisicos**, no GPIO Linux/BCM. J6 tiene dos columnas, una impar y otra par, numeradas desde el extremo de pin1: `1 2`, `3 4`, `5 6`... Evitar guiarse solo por color de jumper.

## 2. Conexiones LOGICAS: cuatro jumpers

| Jetson Nano **J6 (pin fisico)** | Nombre Jetson | PCA9685 | Funcion |
|---:|---|---|---|
| **1** | 3.3 V | **VCC** | Alimentacion del chip PCA9685 y referencia pull-ups del bus |
| **3** | I2C1_SDA | **SDA** | Datos I2C (NO invertir con SCL) |
| **5** | I2C1_SCL | **SCL** | Reloj I2C (NO invertir con SDA) |
| **6** | GND | **GND** | Tierra de referencia comun |

```text
JETSON NANO 2GB / J6                 PCA9685 (header con etiquetas)
[1] 3V3 ---------------------------> VCC      (LOGICA 3.3V)
[3] SDA ---------------------------> SDA      (I2C)
[5] SCL ---------------------------> SCL      (I2C)
[6] GND ---------------------------> GND      (masa)
[17] 3V3              SIN CABLE ---> OE       (en esta fase NO se conecta)
```

**OE en esta fase:** tras la petición del usuario de probar sin 2N2222, se retiro el cable OE→J6 pin17. En una placa Adafruit original, OE tiene pull-down por defecto y puede quedar sin conexion externa, con nivel LOW que PERMITE salidas si se habilitan los registros. En clones, verificar el estado electrico real; el usuario reporto una lectura cercana a 0 V, pero esto **NO es un interlock seguro**. OE LOW no sustituye al STOP. Nunca unir OE a pin17 3.3 V y a GND o un GPIO simultaneamente.

**Prohibido:** confundir **VCC** con **V+**; mandar 5 V de potencia al VCC de 3.3 V en este montaje; conectar VCC a pin 2/4 de 5 V; conectar fuente de servos al pin 1/17 de Jetson; cruzar SDA y SCL.

## 3. Conexion de potencia de servos (separada de Jetson)

La fuente nominal 5 V/10 A alimenta **solamente** los servos a traves del bornero de potencia del PCA9685, no la Jetson ni el VCC de logica:

```text
Fuente DC 5 V/10 A    -> PCA9685 bornero azul de potencia
   +5 V DC (+V)       -> V+
    0 V DC (-V)       -> GND de potencia (borne -)
                          |
                          +-- comun a GND de logica del PCA9685
                              y Jetson J6 pin 6
```

El retorno DC de la fuente de servos y GND de Jetson comparten referencia **a traves de GND de la placa**. No modificar bornes AC ni el STOP existente sin una revision electrica competente. No intercambiar el signo de la bornera, y comprobar su serigrafia real porque clones pueden colocar bornes en posiciones diferentes.

**No aplicar la potencia de servos durante el diagnostico I2C**. Este montaje de potencia estaba conectado previamente y se conserva como configuracion de referencia, NO como instruccion para energizarlo ahora.

## 4. Conectores de servos (seis canales)

| ID | Servo | Canal PCA9685 | Conexion |
|---:|---|---:|---|
| 1 | Base MG995 | 0 | GND / V+ / señal PWM del CH0 |
| 2 | Hombro MG995 | 1 | GND / V+ / señal PWM del CH1 |
| 3 | Codo MG995 | 2 | GND / V+ / señal PWM del CH2 |
| 4 | Muneca 1 SG90 | 3 | GND / V+ / señal PWM del CH3 |
| 5 | Muneca 2 SG90 | 4 | GND / V+ / señal PWM del CH4 |
| 6 | Garra SG90 | 5 | GND / V+ / señal PWM del CH5 |

Colores típicos de servo: negro o cafe = GND; rojo = V+; amarillo/naranja/blanco = señal. **Verificar pinout del servo y etiqueta de la placa antes de insertar**; la orientacion fisica depende de la placa. Los canales 6–15 quedan vacios y deben permanecer deshabilitados. No afirmar que los angulos Home y limites del simulador son posiciones mecanicas calibradas.

## 5. Proxima prueba de diagnostico (sin motor)

Despues de inspeccionar y ajustar **solo con todo apagado** los cuatro jumpers, continuidad extremo a extremo (si se dispone de multimetro) y ausencia de cortos:

- Dejar STOP fisico activado; fuente 5 V de servos sin energia.
- Encender solo Jetson y comprobar ~3.3 V de VCC logico contra GND si se pueden medir con seguridad.
- Sondear solo el dispositivo del PCA9685:

```bash
ssh -T -o ConnectTimeout=10 antonio@jetson-nano.local 'i2cdetect -y -r 1 0x40 0x40'
```

**Si devuelve `40`**: hay respuesta al sondeo, no necesariamente funciones de escritura/registro comprobadas; continuar despues con `status` y `disable-all`, siempre con STOP.
**Si devuelve `--`**: no hay ACK; no intentar movimiento ni inyectar PWM, continuar diagnostico del bus/placa.

## Fuentes consultadas

- [NVIDIA Jetson Nano 2GB Developer Kit User Guide, J6 40-pin header](https://developer.nvidia.com/embedded/learn/jetson-nano-2gb-devkit-user-guide).
- [Adafruit PCA9685 16-channel servo driver pinouts](https://learn.adafruit.com/16-channel-pwm-servo-driver/pinouts).
- [Adafruit PCA9685 wiring for servo driver](https://learn.adafruit.com/16-channel-pwm-servo-driver/hooking-it-up).

## Evidencias del proyecto

- [Bitacora cronologica y fallos I2C](13-bitacora-pruebas-jetson-pca9685.md).
- [Protocolo para prueba futura de un solo servo sin transistor](12-prueba-directa-pca9685-sin-transistor.md).
