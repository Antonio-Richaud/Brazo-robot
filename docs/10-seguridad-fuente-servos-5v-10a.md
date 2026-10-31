# Preparacion segura de la fuente de 5 V / 10 A del brazo robot

**Inicio de fase:** 30 de octubre de 2026.
**Rama:** `feat/jetson-servo-power-safety`, creada desde el merge PR #5 en `main` (`c8d76688bbbb6fd272e3154707ed6948434e5e38`).
**Estado actual (31 de octubre de 2026, declarado por el usuario):** la fuente conmutada nominal de **5 V / 10 A ya esta conectada y alimenta el circuito de potencia del PCA9685**. El usuario indica que realizo correctamente el montaje. **No hay fotos, mediciones de tension/corriente ni inspeccion electrica independiente**; no presentar la instalacion como medida o certificada. Siguiente paso: leer el estado I2C sin habilitar PWM.

**Nota cronologica:** los apartados 1–6 representan el plan previo al primer encendido (30 de octubre). Los textos que describen la fuente como desconectada son historicos y ya no corresponden al estado reportado. No manipular cableado energizado; consultar apartado 7.

## 1. Estado comprobado al abrir esta etapa

- Jetson Nano 2GB (JetPack 4.6.1 / Python 3.6.9) comunicada con PCA9685 por I²C 1, dirección 0x40.
- Según la última prueba efectuada, los 16 canales estaban en FULL OFF; ese registro no sustituye un interruptor físico de alimentación.
- OE del PCA9685 estaba **cableado** a 3.3 V mediante el pin físico 17 del header J6 de Jetson. **NO hay lectura con multímetro que acredite el nivel alto real en OE.**
- Telemetría y dashboard funcionan con simulación matemática, NO controlan la alimentación de los servos.
- La fuente prevista es de 5 V / 10 A; **modelo, entrada AC, selector de tensión, bornes, protecciones y cable exacto todavía no están confirmados mediante fotos de la unidad**.
- Los servos MG995 y SG90 pueden presentar picos de corriente de arranque o bloqueo; los 10 A nominales NO garantizan que puedan moverse los seis a la vez con seguridad.
- **Estado no verificado:** cableado de tierra de protección (PE), fusible/disyuntor, diferencial, sujeción del cable, carcasa que impida tocar la entrada AC, interruptor/corte de emergencia, continuidad de masa, polaridad y salida de fuente medida.

## 2. Exclusiones hasta completar la revision

- No conectar la fuente a la red eléctrica ni energizarla con bornes de red accesibles.
- No tocar ni recablear la fuente con alimentación conectada; pueden permanecer condensadores cargados incluso después de desenchufar.
- No conectar todavía V+ de la fuente a la placa PCA9685 ni alimentar ninguno de los seis servos.
- No conectar el positivo de 5 V a VCC, SDA, SCL, OE ni a ningún pin de 3.3 V de la Jetson.
- No usar Home, Saludo, Rutina, joystick ni órdenes de PWM para una primera prueba.
- No confiar en software, FULL OFF u OE como reemplazo de un corte de potencia físico.

## 3. Puerta de entrada: fotografias y especificaciones

Antes de proponer un circuito o primer encendido, solicitar **fotografías nítidas de la fuente realmente adquirida**:

1. Etiqueta completa con fabricante/modelo, potencia/corriente, INPUT y OUTPUT, símbolos de doble aislamiento o tierra.
2. Bornes, serigrafía y posible selector 115/230 V, sin cables que oculten las marcas.
3. Estado actual del enchufe, cable de alimentación, interruptor, carcasa, fusible/interruptor termomagnético y puesta a tierra.
4. Foto de la placa PCA9685 con etiquetas VCC, GND, V+ y OE visibles, además de las conexiones existentes a Jetson.
5. Confirmar disponibilidad de multímetro y de un método adecuado para desconectar físicamente la potencia de los servos.

No asumir que la fuente tiene selector o que corresponde a entrada 127 V AC por la región; **se determina por su etiqueta real**. Si la fuente expone L/N/PE o contactos de red, el cableado y las comprobaciones de protección deberán realizarlos personal competente en electricidad antes de energizarla.

## 4. Puertas de validacion, todas pendientes

### Etapa A — Inspección eléctrica sin energía

- [ ] Identificar la fuente exacta por su placa y ficha técnica.
- [ ] Comprobar que entrada de red y selector, si existe, coinciden con el suministro del lugar.
- [ ] Validar con persona competente conductor de protección PE, aislamiento, sujeción de cable, carcasa, protección contra cortocircuito y medio de desconexión accesible.
- [ ] Identificar claramente salida DC `+V` y `-V`; no confundir `-V` con conductor AC neutro o PE.
- [ ] Revisar que no existan cables sueltos, cortos entre bornes, tornillos expuestos con tensión, daño o signos de sobrecalentamiento.

### Etapa B — Prueba individual de fuente sin carga y protegida

**Solo después de pasar Etapa A.** Mantener desconectados PCA9685, Jetson y los seis servos de la salida DC. Un electricista o persona competente debe encargarse de toda conexión de red si hay bornes AC expuestos.

- [ ] Alimentar con entrada AC completamente cerrada/protegida y medio de desconexión inmediato disponible.
- [ ] Medir exclusivamente **salida DC** entre `+V` y `-V` con multímetro adecuado; confirmar valor alrededor de 5.0 V y dentro del margen indicado por el fabricante.
- [ ] Confirmar polaridad y ausencia de sobrecalentamiento, olor, ruido anómalo, chispas o caída de tensión.
- [ ] Cortar la alimentación y comprobar descarga/ausencia de tensión antes de recablear.

**No realizar esta prueba si faltan tapa, PE donde sea exigible, alivio de tensión, protecciones o competencia para trabajar con red AC.**

### Etapa C — Interfaz de potencia con el PCA9685, sin mover servos

**No iniciar hasta verificar A y B y tener un diseño revisado de paro físico de potencia.**

- [ ] Medir con instrumento que OE esté realmente en nivel alto (3.3 V lógico) respecto a la referencia GND correcta.
- [ ] Confirmar por lectura I²C los 16 canales FULL OFF inmediatamente antes de cada prueba.
- [ ] Revisar esquema de referencia común DC y protección de Jetson contra retorno de 5 V, tensión inversa y cableado erróneo.
- [ ] Instalar y comprobar un interruptor de corte **físico** de potencia DC de servos, con capacidad apropiada; no confundir con botón de software.
- [ ] Definir fusibles, calibre/longitud de cables, borneras y protección para la corriente y los picos reales.
- [ ] Solo después de revisar conjuntamente esquema y protecciones decidir si conectar V+ al bloque de potencia del PCA9685, **todavía sin ningún servo**.

### Etapa D — Un servo de prueba, posterior y separada

- [ ] Realizar prueba inicial de un único servo, sin carga mecánica, con montaje seguro, zona despejada, limitación de recorrido, paro físico operativo y calibración individual.
- [ ] Comprobar caída de tensión, corriente, calentamiento y reacción a pérdida de control.
- [ ] No alimentar múltiples motores ni conectar la carga completa del brazo hasta tener márgenes eléctricos y mecánicos probados.

## 5. Criterios inmediatos de alto

**Desenergizar y no continuar** si existe selector incorrecto, tierra de protección no verificada, terminales de red expuestos, salida distinta a la nominal, inversión de polaridad, cable calentándose, olor a quemado, chispas, sobrecorriente, ruido inusual, reinicio de Jetson o movimiento espontáneo.

## 6. Proximo paso acordado

**Solicitar las fotos de etiqueta, bornes y cableado actual de la fuente**, sin encenderla. Con esas imágenes elaborar un mapa del circuito real y las precauciones concretas, empezando por la inspección sin energía. El objetivo inmediato no es mover un servo ni activar la fuente de forma improvisada.

**Referencia:** [01-hardware-y-conexiones.md](01-hardware-y-conexiones.md), [08-jetson-pca9685-i2c-pruebas.md](08-jetson-pca9685-i2c-pruebas.md), [09-jetson-simulacion-seis-servos.md](09-jetson-simulacion-seis-servos.md).


## 7. Estado de alimentacion reportado y proximo chequeo (31 de octubre de 2026)

El usuario indica expresamente: **«Ya esta, ya recibe 5V 10A el PCA9685, confia en que ya lo hice correctamente»**. Registrar que **el montaje actual tiene alimentacion en la entrada de potencia del PCA9685**, por fuente de 5 V / 10 A nominales, segun declaracion del usuario. **10 A indica capacidad de corriente de la fuente y NO consumo constante de la placa o de los servos.**

**Limites de verificacion:** las ultimas pruebas de `FULL OFF` 16/16 se realizaron antes de energizar la fuente. El nivel electrico de OE y la tension de V+ no se han medido instrumentalmente en esta conversacion. Tampoco se ha comprobado un corte fisico de emergencia. Estas observaciones no desacreditan el montaje reportado: son pruebas pendientes distintas.

**Paso 10.2, solo lectura:** desde Mac, con la Jetson en red y sin mover conectores:

```bash
ssh -T -o ConnectTimeout=10 antonio@jetson-nano.local \
  'cd "$HOME/robot-lab/Brazo-robot" && python3 jetson/pca9685_safe.py status'
```

Resultado esperado: `Canales FULL OFF: 16/16` y `TODOS DESHABILITADOS: SI`. La herramienta lee registros de I2C; no mide OE ni V+, no emite PWM y no mueve motores.

Si algun servo se mueve inesperadamente, aparece olor, humo, calor anormal o ruido electrico, cortar alimentacion **con el interruptor/desconexion fisica segura**, no tocando bornes ni cables energizados. No ejecutar `disable-all`, pulsos o comandos de movimiento durante esta comprobacion.

**Siguientes decisiones:** confirmar estado de los servos y de la desconexion fisica de potencia, y planificar calibracion de un servo a la vez. Trabajar solo en `feat/jetson-servo-power-safety`.
