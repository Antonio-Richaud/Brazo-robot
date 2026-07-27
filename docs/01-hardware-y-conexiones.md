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
