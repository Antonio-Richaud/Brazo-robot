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

## 8. Paso 10.2 confirmado: PCA9685 FULL OFF con fuente conectada (31 de octubre de 2026)

El usuario ejecuto desde Mac sobre la Jetson real `ssh -T -o ConnectTimeout=10 antonio@jetson-nano.local 'cd "$HOME/robot-lab/Brazo-robot" && python3 jetson/pca9685_safe.py status'` despues de reportar alimentacion de la entrada de potencia V+ con fuente nominal 5 V / 10 A. La conexion SSH funciono (se mostro solo la advertencia ya conocida de negociacion sin intercambio poscuantico).

**Salida observada en la Jetson:**

```text
=== PCA9685 /dev/i2c-1 / 0x40 ===
MODE1: 0x01
MODE2: 0x04
PRE_SCALE: 0x79
Canales FULL OFF: 16/16
TODOS DESHABILITADOS: SI
OE: NO verificable por I2C; mantener OE -> 3.3 V
IMPORTANTE: FULL OFF no reemplaza un corte fisico de potencia
```

**Resultado:** lectura I2C correcta de 16/16 canales con FULL OFF, ya con alimentacion de potencia reportada presente. No se escribio ningun registro, no se habilito PWM, no se comprobo ningun movimiento fisico. El bus indica ~50 Hz nominales por `PRE_SCALE`, no es medicion instrumental de una salida.

**No verificado todavia:** tension real V+ DC y polaridad con multimetro; nivel fisico de OE respecto a GND; integridad del sistema de corte de potencia, puesta a tierra/protecciones y corriente bajo carga. Que el comando lea FULL OFF no demuestra una condicion electrica segura ante cableado, alimentacion o servo defectuoso.

**Puerta de entrada al siguiente paso:** comprobar disponibilidad de multimetro y corte fisico accesible de V+; revisar la salida DC y el estado OE unicamente en el lado de baja tension, evitando terminales AC. Si L/N/PE estan expuestos, no hacer mediciones con la fuente energizada; solicitar revision de una persona electricamente competente. No retirar OE ni enviar PWM hasta validar condiciones previas y planificar un servo de prueba individual.

La rama activa de trabajo es `feat/jetson-servo-power-safety`; `main` permanece como linea base ya fusionada.

## 9. Paso 10.3: 5 V en V+ y 3.3 V en OE reportados (31 de octubre de 2026)

Tras la lectura I2C real `Canales FULL OFF: 16/16`, se solicito comprobar los niveles DC `V+` con respecto a `GND` y `OE` con respecto a `GND`. El usuario respondio: **«Si tiene 5 v y 3.3 v»**. Registrar como **mediciones/valores reportados por el usuario**, no como prueba instrumental independiente ni certificacion de toda la instalacion:

| Punto solicitado | Valor reportado | Interpretacion |
|---|---:|---|
| V+ con respecto a GND de potencia | 5 V DC | Alimentacion nominal de servos presente |
| OE con respecto a GND logico | 3.3 V DC | Nivel alto esperado que inhibe salidas del PCA9685 |

En la prueba anterior la Jetson tambien confirmo por I2C `FULL OFF 16/16`. Por tanto, los tres indicadores son consistentes con el estado esperado para seguir **preparando**, no accionando, motores. La fuente `5 V / 10 A` tiene corriente nominal disponible de hasta 10 A, que no representa consumo fijo de 10 A.

**Pendiente critico antes de permitir siquiera un comando de movimiento:** confirmar un **corte fisico de los 5 V de potencia de servos** accesible, adecuado para corriente DC y **separado de la alimentacion de la Jetson**. OE y FULL OFF no son un paro de emergencia: no cortan V+. Debe validarse tambien que se puede probar un solo servo sin carga, con limites mecanicos y salida deshabilitada por defecto; no retirar OE ni emitir PWM durante esta etapa.

**Siguiente pregunta unica al usuario:** ¿ya hay un interruptor fisico o paro de emergencia que corte la potencia V+ de los servos de inmediato, sin depender del software ni de que la Jetson responda? Si no, disenar y comprobarlo antes de ensayar movimiento. No confundir un boton de control WebSocket/Home con paro fisico.

**Importante:** los valores en V+ y OE no sustituyen validacion de PE de la fuente AC, protecciones contra cortocircuito, calibre de conductores ni comprobacion bajo carga. No tocar bornes ni manipular conectores energizados.

## 10. Paso 10.4: corte fisico reportado, prueba funcional pendiente (31 de octubre de 2026)

El usuario confirmo que **ya tiene instalado un interruptor fisico o paro de emergencia que corta la energia de la fuente de servos independientemente de la Jetson**. Declaracion textual: «Sí ya lo tengo». **Aclaracion posterior del mismo usuario (paso 10.5): el corte esta en el lado AC, entre el enchufe y la fuente conmutada, NO en la salida DC de 5 V.** La confirmacion es del usuario; no constituye prueba documental de la capacidad nominal del contacto, protecciones o verificacion de seguridad.

Condiciones antes de probar: mantener el PCA9685 con FULL OFF 16/16 segun la ultima lectura y OE conectado a nivel alto 3.3 V; no mover servos ni enviar PWM. Apoyar el brazo y asegurar la carga porque quitar potencia puede liberar los ejes. Mantener manos lejos de articulaciones y de bornes de corriente alterna.

**Siguiente verificacion funcional de bajo voltaje (sin cambiar cables):** observar con multimetro el voltaje en el **lado de la alimentacion DC que queda despues del interruptor/paro hacia los servos**. Si el corte esta antes de la entrada V+ del PCA9685, el punto de medida es V+ respecto al GND de potencia de la placa. Accionar el paro y comprobar que en ese lado de carga la tension desciende a aproximadamente 0 V despues de descargar condensadores, mientras la Jetson permanece operativa. Si el corte esta despues de V+ del PCA9685, no usar la medicion V+ como prueba; identificar el lado de carga efectivo sin tocar cableado energizado. No confundir el contacto NA/NC, ni dar por probado el paro solo por accionarlo.

**Criterio para avanzar:** comprobar fisicamente que el paro elimina la potencia de servos y no interrumpe la alimentacion/control de la Jetson; verificacion del rearme solo en fase posterior con OE alto y PWM deshabilitado. Registrar medida y tiempo aproximado de caida. Si hay giro o caida espontanea, calor, chispas, olor o cualquier duda de cableado, no continuar y solicitar revision profesional. Se requiere ademas validar capacidad y protecciones del interruptor/contacto para corriente alterna, fase correcta, puesta a tierra y encapsulado antes de movimientos. El cableado real fue aclarado en el paso 10.5.

**Estado:** esperar resultado de la prueba de corte. No existe codigo nuevo ni movimientos permitidos. El documento conserva el historial de los apartados 1–9 sin reinterpretarlos como el cableado actual.


## 11. Paso 10.5: topologia real del STOP aclarada — corta AC, no V+ (31 de octubre de 2026)

**Aclaracion del usuario:** «SÍ funciona, el stop de emergancia interrumpe la corriente que va del enchufe a la fuente, y esta independiete al eliminador de la jetson».

**Topologia del montaje reportada:**

```text
ENCHUFE CA --- [STOP fisico en entrada AC] --- [FUENTE CONMUTADA 5 V / 10 A] --- V+ y GND potencia del PCA9685 --- SERVOS

ENCHUFE CA --- [ELIMINADOR INDEPENDIENTE JETSON] --- Jetson Nano 2 GB --- VCC logico 3.3 V, SDA/SCL/GND y OE alto del PCA9685
```

Es un **paro aguas arriba de la fuente en el lado de red CA**: al accionarlo, la fuente deja de recibir energia de entrada, mientras la Jetson sigue alimentada por su propio eliminador. Esto **CORRIGE** la suposicion de las notas previas de que el interruptor interrumpia directamente la linea V+ DC. La persistencia temporal de los 5 V en la salida depende de los condensadores de la fuente y de la carga conectada; **la interrupcion de entrada AC no demuestra una eliminacion instantanea de V+**.

**Estado comunicado:** el usuario confirma que el STOP funciona, sin medicion temporal explicita de decaimiento de V+ ni certificado de contacto. Evitar afirmar que el paro tiene capacidad de seguridad normativamente validada.

**Comprobacion pendiente sin modificar conexiones de potencia:** mantener PWM en FULL OFF 16/16 y OE alto; usar multimetro en modo voltaje continuo para observar la salida **V+ respecto a GND de potencia** del PCA9685 (solo bornes de baja tension, sin acercarse a L/N/PE de CA). Al activar STOP, la tension debe caer de ~5 V a ~0 V; registrar si tarda segundos en desaparecer. La Jetson debe permanecer encendida. No puentear el STOP ni recablearlo con alimentacion conectada.

**Seguridad de la entrada AC:** el dispositivo y contactos del STOP tienen que estar dimensionados para la entrada de red, en caja protegida y con cables fijados; confirmar que interrumpe el conductor de fase (no solamente neutro) y **nunca** el conductor de proteccion PE. Una fuente con bornes CA expuestos requiere revision/cableado por profesional competente. No considerar un contacto improvisado equivalente a parada de emergencia certificada.

**Siguiente paso:** observar la caida de V+ con STOP accionado y Jetson encendida, y mantener STOP activado al terminar. No habilitar PWM ni tratar de mover uno o varios servos en esta comprobacion.


## 12. Paso 10.5b: corte de potencia y logica independiente confirmados (31 de octubre de 2026)

El usuario aclara: **«Cuando acciono el stop le deja de llegar corriente a las clemas de potencia pero sigue teniendo los 3.3 v de la jetson porque esa sigue encendida»**.

**Estado observado y reportado:** al accionar el paro situado antes de la fuente conmutada de potencia, deja de suministrarse alimentación a las clemas V+ del PCA9685; la Jetson Nano continua encendida con su eliminador independiente, por lo que la alimentación logica 3.3 V permanece. Esto valida funcionalmente la **separacion de alimentacion logica y potencia ante el STOP**, sin necesidad de que el software actue para apagar la fuente.

**Limites:** la respuesta no proporciona una lectura numerica de 0.00 V, tiempo de descarga de condensadores ni certificacion electrica del interruptor, la entrada AC o el conductor PE. No declarar estos puntos comprobados. El estado previo de I2C era FULL OFF 16/16, y el pin OE se habia medido a 3.3 V en funcionamiento. Si el brazo tiene piezas bajo carga, al cortar potencia los ejes pueden liberarse.

**Paso 10.5 cerrado funcionalmente**, manteniendo como pendientes la revision de protecciones AC, capacidad del STOP, control del rearranque y las pruebas mecanicas. No emitir comandos PWM ni retirar OE en esta fase.

**Siguiente paso 10.6 (preparacion, sin movimiento):** seleccionar un unico servo pequeño, preferentemente SG90 del canal 5 (garra), para una futura prueba **desacoplado mecanicamente de la garra o sin carga**, con el brazo estable y sin riesgo de pellizcos. Confirmar que se puede aislar el servo de la mecanica; si no se puede, no probar movimiento desde el software. Toda manipulacion de conectores se hace con la fuente de servos y la Jetson desenergizadas, no solo con STOP. No rearmar STOP hasta definir el control individual con arranque seguro, watchdog, limites y un medio de corte probado.


## 13. Paso 10.6: brazo ensamblado — primer servo sin desacoplar (31 de octubre de 2026)

**Nueva confirmacion del usuario:** «Todo esta acoplado en la documentacion tienes todo lo necesario». Los seis servomotores siguen montados y acoplados mecanicamente al brazo; no pedir de nuevo que se desacople la garra ni presentar un servo aislado sobre la mesa como estado actual. Los archivos existentes describen la arquitectura, asignacion de canales y limites logicos, pero **NO documentan calibracion fisica de orientacion del horn, topes/recorridos realmente comprobados ni los angulos actuales medidos**. Los motores MG995/SG90 actuales no aportan encoder al controlador.

### Inventario existente (ver docs/01 y config.py)

| Servo ID | Articulacion | Motor | Canal PCA9685 | Home LOGICO | Limites LOGICOS (sin calibrar) |
|---|---|---|---:|---:|---|
| 1 | Base | MG995 | 0 | 90 grados | 10-170 |
| 2 | Hombro | MG995 | 1 | 50 grados | 15-165 |
| 3 | Codo | MG995 | 2 | 165 grados | 15-165 |
| 4 | Muneca vertical | SG90 | 3 | 10 grados | 10-170 |
| 5 | Giro de muneca | SG90 | 4 | 170 grados | 10-170 |
| 6 | Garra | SG90 | 5 | 40 grados | 20-140 |

### Hallazgos de codigo antes de cualquier movimiento acoplado

1. `jetson/pca9685_safe.py` **solo permite `status` y `disable-all`**, sin API de habilitar servos, y la simulacion `jetson/arm_simulation.py` no tiene transporte fisico. No existe un comando seguro de la Jetson para mover un unico servo actualmente.
2. **OE sigue conectado fisicamente a 3.3 V**, por lo que todas las salidas deben permanecer inhibidas hasta disenarse y verificar un control de habilitacion de señal a prueba de fallos. Nunca cortocircuitar OE ni retirarlo con potencia energizada.
3. `robot_arm_controller/robot_arm_controller.ino` utiliza pulsos generales de 500-2500 us y en `setup()` ejecuta `writeAllServosCurrent()` con posiciones Home predefinidas. **Ese firmware ESP32 puede ordenar inmediatamente posiciones Home a los seis servos al arrancar**; no usarlo ni iniciar el backend `--mode hardware` como atajo para la primera prueba Jetson con todos los ejes montados.
4. La interfaz WebSocket de la Mac en modo Jetson replay es de **solo lectura** y sus 10 controles permanecen bloqueados. No habilitar Home, Saludo ni Rutina del brazo fisico.
5. El paro del usuario esta en el **lado AC de la fuente de potencia**, independiente de la fuente de Jetson; se reporto corte correcto de la alimentacion V+ pero aun no hay medicion de tiempo de descarga ni validacion de todos los aspectos de seguridad electrica.

### Criterios del primer ensayo, sin desmontar el brazo

- Se puede usar el SG90 de garra (servo ID6, canal 5) **montado**, pero sin objeto sujetado y con zona despejada; el acoplamiento significa que NO es una prueba sin carga mecanica. La direccion de cierre/apertura, los topes y la posicion real del horn permanecen desconocidos; no suponer que el valor `40 grados` es mecanicamente seguro.
- Brazo apoyado/asegurado frente a perdida de par de otros ejes; nadie dentro del alcance, sin carga sostenida por gravedad o piezas que puedan caer.
- Diseñar controlador de **unico canal autorizado** con estado seguro por defecto, otros 15 canales FULL OFF, habilitacion explicita bajo confirmacion humana, movimiento incremental de amplitud acotada y vigilancia de tiempo y fallos, y **deshabilitacion automatica** al terminar o perder enlace. La rutina NO debe mover a Home al iniciar, al terminar ni ante un error.
- La habilitacion del canal 5 requiere resolver por diseño el bloqueo OE alto, sin modificar cableado bajo tension y conservando deshabilitacion segura al reiniciar/caer el controlador; requiere validar modo de falla y acceso al paro fisico.
- Antes de ejecutar movimiento real, calibrar el punto inicial con medios compatibles con el montaje (documentar posicion y libertad de recorrido) y validar direccion/rangos de pulso reales; un cambio minimo en el objetivo puede producir un salto importante en el **primer pulso** si no se conoce la posicion actual.
- Mantener en `FULL OFF 16/16` y OE alto hasta completar diseño, pruebas simuladas del controlador y preflight fisico. **No emitir `home`, `s 6 ...`, `d 6 ...`, ni ejecutar la ruta ESP32 de forma fisica ahora.**

**Decision actual:** no desmontar por defecto. Preparar primero software y protocolo especificos del servo de la garra acoplado; conservar todo en `feat/jetson-servo-power-safety`, sin cambiar `main`. No declarar que los limites logicos son una calibracion fisica.


## 14. Paso 10.7: Jetson.GPIO disponible; OE permanece inhibido (31 de octubre de 2026)

**Evidencia ejecutada por el usuario desde Mac (SSH autenticado a `antonio@jetson-nano.local`):**

```text
JETSON_GPIO_DISPONIBLE
Version: 2.0.17
```

El script realizo **solo `import Jetson.GPIO as GPIO` y leyo `GPIO.VERSION`**. No llamo `setmode`, `setup`, `output`, `input`, `cleanup`, ni cambio la direccion, nivel o multiplexor de ningun pin. Confirmado: la libreria **Jetson.GPIO 2.0.17 esta disponible** bajo Python 3.6 del sistema JetPack 4.6.1. Esto NO implica que exista un GPIO de control de OE ya cableado.

### Advertencia electrica imprescindible para la siguiente etapa

- Actualmente el pin **OE del PCA9685 esta unido directamente al riel de 3.3 V del header J6, pin fisico 17**. El pin 17 es una **alimentacion fija de 3.3 V, NO un GPIO programable**.
- Segun la ficha oficial NXP PCA9685, **OE es activo en BAJO**: con OE alto las salidas estan inhibidas segun la configuracion OUTNE del MODE2; con OE bajo siguen los registros PWM. La ultima medicion reportada en OE es 3.3 V y la lectura PCA9685 confirmo FULL OFF en los 16 canales.
- **PROHIBIDO** conectar directamente un GPIO configurado como salida a OE mientras OE permanezca unido al pin 17 de 3.3 V: una salida BAJA entraria en conflicto con el riel de 3.3 V, con riesgo de dano electrico a la Jetson.
- La disponibilidad de Jetson.GPIO no crea una proteccion ante bloqueo del proceso Linux, reboot, kernel panic, perdida de red o alimentacion independiente de los servos. No suponer que un `finally` de Python puede detener el motor tras un fallo del sistema.
- En placas PCA9685 comerciales, el estado default de OE y las resistencias montadas pueden variar: identificar el modulo exacto y su red de pull-up/pull-down antes de definir resistencias, transistor o un pin J6 adicional.

### Arquitectura propuesta (NO cableada ni implementada)

1. Mantener `FULL OFF` en 16 canales y dejar OE alto durante todo el diseño y pruebas de software.
2. Un circuito de **inhibicion por defecto** externo al programa mantiene OE ALTO cuando no hay autorizacion, durante arranque/reinicio o si se desconecta el control. La etapa que podria tirar OE a BAJO debera ser de tipo transistor adecuado (salida de colector abierto/open-drain o equivalente) y no una salida GPIO conectada en paralelo con la alimentacion 3.3 V.
3. El eventual permiso de OE debe depender de un **interlock/watchdog independiente**, no solo de un valor GPIO mantenido; y no debe puentear el STOP fisico de potencia. Se diseñara y validara un estado a prueba de fallos antes de energizar el control de movimientos.
4. El control de un unico canal requiere tambien validacion de rango de pulsos fisicamente calibrado, lectura de `FULL OFF` de todos los otros canales, arranque sin Home automatico, supervision de tiempo y deshabilitacion inmediata del canal ante error.
5. Primero revisar esquema y luego ensayar **sin movimiento**, con medidor de OE y potencia de servos cortada. Cualquier ensayo real con la garra mecanicamente acoplada es una fase posterior, con trayecto, cargas y riesgos mecanicos conocidos.

### Siguiente paso 10.8

Antes de decidir el GPIO concreto, **identificar el modelo/revision del modulo PCA9685 y la red OE instalada** (fotografia frontal/reverso o referencia exacta; inspeccion fisica con potencia retirada), y definir la topologia de inhibicion y watchdog independiente. No manipular el pin 17 energizado. Las alternativas de interfaz y sus componentes exactos se definiran para ese modulo, no por suposicion.

**Referencias tecnicas:**
- NXP PCA9685, seccion 7.4 de ficha tecnica oficial: https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf
- NVIDIA Jetson.GPIO API y pin numeration BOARD: https://github.com/NVIDIA/jetson-gpio


## 15. Paso 10.8: placa PCA9685 identificada por fotografia frontal (31 de octubre de 2026)

El usuario compartio una fotografia cercana del modulo montado. **Inspeccion visual**: placa PCB azul tipo Adafruit PCA9685 16-channel / 12-bit PWM Servo Driver; se observan serigrafias `VCC`, `SDA`, `SCL`, `OE`, `GND`, un banco de conectores de servos con cables instalados, bornera de dos tornillos de potencia, un condensador electrolitico grande y LED indicador `POWER` encendido. Se observa una serigrafia `adafruit`, pero **no se puede confirmar si el modulo es original o una copia solo por una imagen frontal**. El lado posterior/trazado OE y la red de resistencias no son visibles con suficiente detalle para certificar sus valores.

**Distincion electrica importante:** el LED `POWER` no demuestra que la linea OE sea segura ni que la señal PWM esté habilitada; es solo un indicador de alimentacion del modulo. Las mediciones previas del usuario de V+ ~5 V y OE ~3.3 V y lectura I2C `FULL OFF 16/16` permanecen como registros separados.

**Datos corroborados con fuentes tecnicas:**

- Adafruit documenta para el breakout de 16 canales OE activo BAJO (LOW habilita las salidas / HIGH deshabilita), con **pull-down por defecto** en su propia version; por lo tanto, si se retira el cable que eleva OE a 3.3 V, NO debe asumirse que OE seguira alto ni que las salidas permaneceran inhibidas. Las copias pueden diferir y su topologia exacta no ha sido verificada. Fuente: https://learn.adafruit.com/16-channel-pwm-servo-driver/pinouts
- NXP especifica que OE activo BAJO habilita salidas de acuerdo con los registros, y HIGH les aplica el estado OUTNE de MODE2. Fuente: https://www.nxp.com/products/power-drivers/lighting-driver-and-controller-ics/led-drivers/16-channel-12-bit-pwm-fm-plus-ic-bus-led-driver%3APCA9685
- El pin fisico 17 del header J6 de Jetson es **3.3 V fijo**, no GPIO programable. Esta conectado a OE segun cableado de la bitacora. **Nunca conectar un GPIO de salida que pueda pasar a LOW en paralelo con esta conexion directa**.

### Conclusion y siguientes acciones (SIN ENERGIZAR MOVIMIENTO)

1. El modulo es compatible visualmente con el PCA9685 de 16 canales que la Jetson detecto en direccion I2C 0x40; la foto no acredita el origen comercial exacto.
2. **No retirar ni mover el cable de OE de 3.3 V ahora**; no unir OE directamente a GND mientras esté unido al pin 17. Si en el futuro se reconfigura este cableado, hacerlo con **Jetson y fuente de servos desconectadas y sin energia residual**, despues de revisar el esquema completo.
3. Preparar una interfaz electronica **de bloqueo por defecto en HIGH** a OE, tomando en cuenta cualquier pull-down montado en el PCB. El permiso para bajar OE a LOW debe depender de una etapa aislada de salida tipo colector abierto/open-drain, con interlock y watchdog **externo** o mecanismo equivalente seguro ante bloqueo de Linux. No asignar componentes ni GPIO concreto hasta conocer correctamente carga y topologia de OE.
4. Mantener FULL OFF en los 16 canales de momento. Para el ensayo posterior de garra montada, el software debe autorizar como maximo un canal con verificacion de todos los demas en FULL OFF, sin Home automatico ni velocidad brusca, con calibracion mecanica previa y paro fisico accesible.
5. **Proxima tarea util sin cables:** disenar y probar en la rama el contrato y las pruebas de un supervisor de seguridad en modo virtual (DISARMED al iniciar, autorizacion explicita, timeout, fault latch, un canal permitido, resto FULL OFF), sin ninguna llamada a hardware; luego concretar materiales y probar la interfaz con el STOP accionado.

**No se modifico ni se habilito ningun motor a raiz de esta fotografia.**


## 16. Cierre documental del 31-10-2026 y plan con 2N2222

**El usuario decidio cerrar la sesion y continuar en otro dia.** Confirmo disponer de multiples transistores 2N2222 y solicito plan completo de lo necesario para lograr un sistema fiable, por que y orden de implementacion, con merge de toda la documentacion a `main`.

El diseño queda en [11-plan-habilitacion-fisica-2n2222.md](11-plan-habilitacion-fisica-2n2222.md): arquitectura de pull-up que mantenga OE HIGH, transistor 2N2222 en configuracion de colector abierto para habilitar OE LOW bajo permiso, resistencias dimensionadas tras caracterizar OE, watchdog/interlock independiente de Linux y protocolo de pruebas OFF → un unico canal → primer SG90 de garra ya montado. El 2N2222 **no sustituye** paro fisico ni watchdog; no hay modificaciones al circuito ni firmware en esta fase.

**Motivos de seguridad:** el OE de breakout tipo Adafruit puede estar tirado a LOW por defecto; retirar sin mas la union directa OE→3.3 V lo habilitaria. Conectar GPIO LOW mientras OE esta atado al pin fijo J6-17 de 3.3 V crearia contencion electrica. Todos los servos siguen acoplados y sus HOME son valores logicos no calibrados. El firmware ESP32 arranca escribiendo HOME a los seis: no usarlo como atajo.

**Cierre seguro solicitado:** STOP de potencia AC activado **antes** de apagar Jetson, para evitar que desaparezcan 3.3 V de OE mientras el riel de servos siga activo. SSH desde Mac: `ssh -t -o ConnectTimeout=10 antonio@jetson-nano.local 'sudo shutdown -h now'`. Esperar cierre limpio y desconectar eliminador de Jetson despues. **No consta aun salida del usuario confirmando que haya ejecutado el apagado**; no marcarlo como verificado.

Al reiniciar trabajo: actualizar `main`, crear rama nueva y empezar por Fase A del plan (identificacion de componentes y diseño sin movimiento), no energizar el brazo automaticamente.
