# Hardware y conexiones

## Arquitectura general

El sistema esta dividido en dos partes:

1. **Potencia**: servos alimentados por una fuente externa de 5V / 10A.
2. **Control**: ESP32 + PCA9685, con comunicacion I2C.

Esta separacion evita que los picos de corriente de los servos tumben al ESP32.

## Conexion del ESP32 al PCA9685

- 3.3V del ESP32 -> VCC logico del PCA9685
- GND del ESP32 -> GND del PCA9685
- GPIO 21 del ESP32 -> SDA del PCA9685
- GPIO 22 del ESP32 -> SCL del PCA9685

## Alimentacion de servos

- Fuente externa 5V / 10A -> terminal de potencia del PCA9685
- GND de la fuente unido al GND del PCA9685
- GND del PCA9685 unido al GND del ESP32

## Regla critica

Todos los **GND deben estar unidos**:

- GND fuente de servos
- GND PCA9685
- GND ESP32

Sin tierra comun, las senales PWM pueden comportarse de forma erratica.

## Servos del sistema

### Alta fuerza
- Base: MG995
- Hombro: MG995
- Codo: MG995

### Ligera / precision
- Muneca eje 1: SG90
- Muneca eje 2: SG90
- Garra: SG90

## Mapeo actual de canales

| Articulacion | Canal PCA9685 |
|--------------|---------------|
| Base         | 0             |
| Hombro       | 1             |
| Codo         | 2             |
| Muneca1      | 3             |
| Muneca2      | 4             |
| Garra        | 5             |

## Consideraciones mecanicas

- El `home` real se ajusto con el brazo ya ensamblado.
- Algunas articulaciones estan cerca de extremos mecanicos, por eso se definieron rangos de seguridad en software.
- El proyecto esta construido en PLA, por lo que el peso no es alto, pero aun asi se debe evitar golpear topes con velocidad.

## Recomendaciones practicas

- Nunca energizar el sistema con servos atorados mecanicamente.
- Evitar cargar peso durante las pruebas iniciales.
- Probar un eje a la vez si se cambian rangos.
- No abrir Monitor Serial y script Python al mismo tiempo usando el mismo puerto USB.
