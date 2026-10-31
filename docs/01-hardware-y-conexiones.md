# Hardware y conexiones

## Potencia y control

El brazo separa la potencia de los servos de la alimentacion logica:

- ESP32 y logica del PCA9685: alimentacion logica.
- Servos: fuente externa estabilizada de 5 V / 10 A.
- Todas las tierras deben compartir referencia.

| ESP32 | PCA9685 |
|---|---|
| 3.3 V | VCC logico |
| GND | GND |
| GPIO 21 | SDA |
| GPIO 22 | SCL |

La fuente de 5 V se conecta al terminal de potencia del PCA9685, nunca al pin
de 3.3 V del ESP32.

## Jetson Nano 2GB + PCA9685 (prueba I²C, sin motores)

**Esta conexión es una alternativa experimental al ESP32**, no implica
que el brazo ya sea controlable desde la Jetson. Se usa el conector
**J6** de 40 pines físicos de la Jetson Nano 2GB, a nivel lógico de 3.3 V.

| Jetson J6 (pin físico) | PCA9685 |
|---|---|
| 1: 3.3 V | VCC lógico |
| 3: SDA | SDA |
| 5: SCL | SCL |
| 6: GND | GND |
| 17: 3.3 V | OE (alto = salidas PWM inhibidas) |

Bus probado: **/dev/i2c-1**, dirección **0x40**. El 30-10-2026
se verificó detección y lectura/escritura de registros, frecuencia nominal
de ~50 Hz, FULL OFF y OE conectado a 3.3 V; **no se energizaron motores**.

Nunca conectar a la vez el ESP32 y la Jetson a las señales de lógica
sin diseñar expresamente la topología eléctrica. La fuente de 5 V / 10 A
de servos va a **V+**, no a VCC; permanecerá apagada durante esta fase.
La inhibición OE y FULL OFF no sustituyen un interruptor físico de corte
de potencia. Ver detalles en
[08-jetson-pca9685-i2c-pruebas.md](08-jetson-pca9685-i2c-pruebas.md).

## Actuadores

| ID | Articulacion | Servo | Canal | Home | Limite |
|---:|---|---|---:|---:|---:|
| 1 | Base | MG995 | 0 | 90° | 10–170° |
| 2 | Hombro | MG995 | 1 | 50° | 15–165° |
| 3 | Codo | MG995 | 2 | 165° | 15–165° |
| 4 | Muñeca vertical | SG90 | 3 | 10° | 10–170° |
| 5 | Giro de muñeca | SG90 | 4 | 170° | 10–170° |
| 6 | Garra | SG90 | 5 | 40° | 20–140° |

Los pulsos del firmware todavía usan 500–2500 µs para todos los servos. Antes
de ampliar limites se debe calibrar cada modelo individualmente para evitar
zumbido, calentamiento y golpes contra topes.

## RealSense D435i

Equipo previsto:

- Modelo: Intel RealSense D435i.
- Identificador de unidad: K38179-100.
- Numero de serie: `926522071007`.
- Interfaz recomendada: USB 3.

La posicion final de montaje debe definirse antes de calcular la transformacion
extrinseca `camara -> base del robot`. El software considera esa calibracion
pendiente y no habilita autonomia con una nube sin registrar.

## Reglas de seguridad

- No conectar o desconectar servos con la fuente energizada.
- No probar nuevos limites con carga en la garra.
- Mantener libre el volumen de movimiento al arrancar.
- No confundir `Cancelar / Home` con paro de emergencia: ese comando produce
  movimiento.
- Añadir un interruptor fisico que corte la potencia de los servos antes de
  habilitar planeacion autonoma.


## Actualizacion de montaje (31-10-2026)

La descripcion inicial de esta guia (fuente de servos apagada durante las pruebas
I2C) corresponde al **estado historico del 30-10**. Segun confirmacion posterior
del usuario, la fuente conmutada nominal 5 V / 10 A ya alimenta las clemas
V+ del PCA9685; se han comunicado medidas de ~5 V en V+ y ~3.3 V en OE.
La lectura I2C de la Jetson volvio a confirmar FULL OFF en los 16 canales
despues de conectar la fuente. El STOP instalado interrumpe la **entrada AC
de la fuente de servos** y deja a la Jetson alimentada por su eliminador
independiente; no esta instalado como corte directo de V+ DC.

Los seis servos siguen **montados y acoplados**. Todavia no existe control
Jetson que habilite PWM fisico con arranque seguro; el modulo
`jetson/pca9685_safe.py` solo expone `status` y `disable-all`.
El firmware ESP32 anterior ordena HOME a los seis ejes en `setup()`, por
lo que no debe ejecutarse para hacer una primera prueba fisica.

**Para continuar:** consultar
[Plan de habilitacion con 2N2222, watchdog y un solo servo acoplado]
(11-plan-habilitacion-fisica-2n2222.md) y
[bitacora de fuente y STOP](10-seguridad-fuente-servos-5v-10a.md).
No unir GPIO directamente a OE mientras permanezca conectado a J6-17
3.3 V. Corte de potencia antes de apagar Jetson, no mover servos
sin los requisitos de la fase A-C del plan.
