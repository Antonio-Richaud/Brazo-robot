# Plan de integracion fisica: Jetson Nano + PCA9685 + 2N2222

**Estado:** PLAN DE DISEÑO, NO IMPLEMENTADO NI AUTORIZADO PARA MOVER MOTORES.
**Fecha de planificacion:** 31 de octubre de 2026.
**Linea base:** PR #5 fusionado a `main`; esta fase se documenta en `feat/jetson-servo-power-safety` antes de fusionarse.
**Objetivo:** controlar inicialmente un SG90 de garra (ID 6, canal PCA9685 5) **ya montado y acoplado**, sin hacer que el resto del brazo se mueva, sin arranque hacia Home y sin tener que desmontar servos por defecto.

## 1. Inventario y hechos comprobados

| Elemento | Estado documentado |
|---|---|
| Jetson Nano 2GB original | Ubuntu 18.04 / JetPack 4.6.1 / Python 3.6.9; SSH `antonio@jetson-nano.local` |
| Jetson.GPIO | **Version 2.0.17**, importada correctamente en la Jetson real; **ningun pin se configuro** |
| PCA9685 tipo Adafruit 16 canales, direccion 0x40 | Identificado visualmente, comunicacion real `/dev/i2c-1`, `MODE1=0x01`, `MODE2=0x04`, `PRE_SCALE=0x79` |
| Salidas PCA9685 | **FULL OFF 16/16**, leido por I2C despues de conectar potencia |
| Alimentacion de servos | Fuente conmutada nominal 5 V / 10 A; usuario reporta ~5 V en V+ del modulo |
| Alimentacion logica | VCC a 3.3 V de Jetson J6 pin fisico 1; OE a 3.3 V **directos** desde J6 pin fisico 17 (valor medido segun usuario) |
| Seguridad de energia | Usuario reporta STOP fisico que **corta entrada AC de la fuente 5 V**, independiente del eliminador de la Jetson; al activarlo deja de alimentarse V+ |
| Actuadores | Seis servos **montados y acoplados**: 3 MG995 en canales 0,1,2 y 3 SG90 en canales 3,4,5 |
| Componentes disponibles | El usuario tiene **varios transistores 2N2222**; resistencias, encapsulados, instrumentos adicionales y supervisores aun por verificar |

**Advertencia de alcance:** las pruebas de GPIO fueron importacion de libreria, las de I2C fueron sin PWM habilitado. No existe aun una prueba fisica de angulos/calibracion del montaje. Los datos `current` del firmware son estimaciones, no lectura por encoder.

## 2. Por que no basta con mover los servos

1. El `OE` del PCA9685 es **activo en nivel bajo**: LOW permite los PWM de los canales; HIGH los inhibe. La placa tipo Adafruit puede tener un pull-down interno de placa hacia LOW; dejar OE sin conexion puede **habilitar salidas**, no apagarlas.
2. Hoy OE esta unido **directamente** a 3.3 V del pin fisico 17, que es alimentacion fija y NO GPIO. Conectar una salida digital LOW a ese mismo nodo crearia un cortocircuito contra los 3.3 V.
3. Los 16 canales se encuentran con `FULL OFF`; para mover un unico servo hay que programar un pulso valido solo para ese canal, y habilitar la señal solamente cuando las verificaciones sean satisfactorias. Al cambiar OE a LOW se habilitan **globalmente** las salidas que no esten en FULL OFF.
4. El firmware ESP32 previo escribe seis HOME en `setup()` y utiliza pulsos generales 500–2500 microsegundos; no se debe activar ese firmware como atajo con los seis servos acoplados. Un primer pulso puede producir un salto a una posicion fisica no calibrada, incluso si el objetivo digital parece pequeno.
5. Un GPIO que permanece HIGH durante un bloqueo de Linux puede dejar activado el transistor y OE en LOW. **Un 2N2222 por si solo NO es watchdog ni paro de emergencia.**

## 3. Arquitectura electrica propuesta (aun no cablear)

```text
                          LOGICA 3.3 V, AISLADA DE V+ SERVO

J6 3.3 V --- R_OE_PULLUP ---+---------------------> OE del PCA9685
                             |
                             +--- C (colector) Q1 2N2222 NPN
                                      E (emisor) -----> GND comun logico

GPIO habilitado SOLO por interlock/watchdog -- R_BASE --> B (base) Q1
                                                       |
                                                 R_BASE_PULLDOWN
                                                       |
                                                       +-----> GND comun logico

Fuera de este dibujo: interlock / watchdog fisico independiente que haga imposible
mantener permiso de OE si se pierde el heartbeat o el controlador se bloquea.

Potencia: ENCHUFE AC -- STOP fisico -- fuente 5 V / 10 A -- V+ del PCA9685
Control: Jetson, con eliminador independiente; NO conectar salida 5 V a 3.3 V.
```

**Atencion:** el dibujo es conceptual, no un plano listo para construir. Los terminales C, B y E son conexiones FUNCIONALES del transistor; su orden fisico depende de la version concreta del 2N2222 y debe verificarse antes de cablear. Esta representacion no incluye aun la logica fisica del watchdog/interlock ni sus componentes dimensionados. La señal de permiso del GPIO solo podra actuar a traves de la compuerta/interlock de habilitacion prevista. El 2N2222 actua como **sumidero de corriente de OE**, no suministra la potencia de ningun servo.

### Componentes previstos y razon

| Componente | Para que | Condicion antes de fijarlo |
|---|---|---|
| 1 x 2N2222 o PN2222A (NPN) | Colector abierto: tirar OE a LOW solo cuando se autoriza movimiento | Confirmar **pinout del encapsulado real** con su datasheet; E/B/C varia por fabricante y tipo |
| R de pull-up OE a VCC 3.3 V | Mantener OE en HIGH si transistor/GPIO estan apagados | Medir el pull-down real de la placa: **el modulo tiene pull-down por defecto segun Adafruit**; dimensionar para OE >= VIH con margen (objetivo cerca de 3.3 V) |
| R en serie con base | Limitar corriente de salida GPIO y fijar saturacion del transistor | Calcular con R_pullup elegida, corriente de colector e IO de Jetson |
| R pull-down base a GND | Mantener el transistor cortado mientras el GPIO esta en entrada/alta impedancia durante arranque | Confirmar corriente de fuga y estado de arranque del pin J6 seleccionado |
| Interlock/watchdog de hardware | Retirar el permiso a OE si desaparece el heartbeat; no depender de un `finally` Python | Definir circuito independiente (supervisor/monoestable o microcontrolador dedicado) y probar fallos antes de accionar motores |
| Protección eléctrica y montaje | Evitar sueltos, daños y reinicios | Resistencia real, diagrama, protoboard solo para pruebas de baja tension con potencia de servo CORTADA; montaje definitivo en soporte/caja segura |

**Valores de calculo preliminares (NO lista de conexion definitiva):** como punto de estudio se pueden evaluar pull-up OE ~1 kOhm, R_BASE ~4.7 kOhm y pull-down de base ~47 kOhm. Pero sin confirmar la resistencia OE de esta placa, el umbral electrico, el pinout del 2N2222 y el GPIO, **no autorizar su montaje**. Por ejemplo, con VCC 3.3 V y un pull-down de placa de 10 kOhm, un pull-up externo de 4.7 kOhm deja OE aproximadamente en 2.24 V, por debajo del VIH especificado (0.7 x 3.3 V = 2.31 V): se deberia medir, calcular y dar margen. Con 1 kOhm y 10 kOhm hipoteticos, OE ronda 3.0 V, pero la impedancia real de esta tarjeta puede ser distinta.

**Cableado actual que debe cambiar en un futuro (NUNCA energizado):** reemplazar el enlace OE -> J6 pin 17 **directo** por el circuito de pull-up + colector abierto probado; no sumar una salida GPIO en paralelo al enlace directo. El 3.3 V para la pull-up nunca sera V+ 5 V. No modificar, tocar ni retirar conectores mientras la Jetson, la fuente o condensadores puedan aportar energia.

## 4. Comportamientos necesarios en una version correcta

### Matriz de estados del sistema

| Evento | OE requerido | PCA9685 canales | Potencia servo | Movimiento |
|---|---|---|---|---|
| Jetson arranca o se reinicia | HIGH por hardware | 16 x FULL OFF al inicializar | STOP activado durante inicio | Prohibido |
| Proceso Python inactivo, GPIO flotante | HIGH por pull-up externa | Sin orden de habilitar | Mantener STOP mientras no haya preflight | Prohibido |
| Preflight aprobado, servos aun desconectados de señal habilitada | HIGH | 16 x FULL OFF | STOP activado | Prohibido |
| Permiso confirmado, un servo de garra seleccionado y calibrado | LOW solo en ventana habilitada y con watchdog independiente | Canal 5 programado; otros **15 en FULL OFF** | Requiere autorización de operador, STOP accesible | Exclusivamente garra, amplitud y tiempo limitados |
| Falla de validacion, timeout, paro, cierre del proceso o comunicacion perdida | HIGH por hardware/interlock; FULL OFF tan pronto como sea posible | 16 x FULL OFF cuando haya bus, sin depender de esto para cortar energia | STOP corta AC de la fuente independientemente | Prohibido; no volver a HOME |
| Jetson apagada | OE no se presupone valido si VCC desaparece | Estado de registros no garantizado | **STOP activado antes** de apagar Jetson | Prohibido |

**Invariante:** el paro de entrada AC no garantiza caída instantánea de V+ (capacitores). No considerar el 2N2222 o GPIO sustitutos de un paro independiente. Para funcionamiento unattended/autonomo se debe mejorar el circuito de seguridad y verificar fallas en todos los escenarios.

### Requisitos de software Jetson Python 3.6

- Modulo nuevo separado del `jetson/pca9685_safe.py` actual, conservando `status` y `disable-all` sin efectos de habilitar.
- Estados explicitos `DISARMED`, `PRECHECK`, `ARMED_SINGLE`, `FAULT_LATCHED` con transiciones y autorizacion local del operador; no arranque armado automatico.
- Canal permitido inicial fijo `5` (servo ID 6, garra); rechazar `0..4` y `6..15`; nunca enviar PWM global a todos.
- Al iniciar: mantener OE HIGH; leer registros PCA9685 y confirmar `0x40`, frecuencia ~50 Hz, 16 FULL OFF, tipo de modo de salida; negar autorizacion si hay divergencia.
- No usar `home`, `saludo`, `rutina`, `stop` de retorno a Home ni `main.py --mode hardware` para esta prueba. El STOP del firmware anterior NO es E-stop.
- Programar solo canales autorizados con verificacion de lectura tras escritura; los demas deben seguir `FULL OFF` incluso despues de excepciones.
- Calibracion REAL de pulsos y recorrido del servo con garra acoplada, sin suponer que 40 grados logicos coincide con el angulo mecanico o que la primera orden sera de amplitud pequena. Los rangos previos 20-140 grados **no fueron calibrados en montaje fisico**.
- Supervisar heartbeat, timeout monotono y errores de bus, con estado FAULT que necesita rearme consciente, nunca recuperacion automatica de movimiento. **No se permite habilitar OE con solo un watchdog cooperativo Python**.
- Si falla el proceso, la red o el equipo, el hardware independiente debe inhibir OE; no confiar en que Linux programe FULL OFF a tiempo.
- Exponer telemetria de estado como **estimada**, nunca `measured=true` en ausencia de encoder, y mantener el monitor actual 8767 de solo lectura.

## 5. Orden de trabajo para la proxima sesion

### Fase A. Inspeccion y diseño (sin tocar el brazo)

- [ ] Releer `docs/01`, `08`, `09`, `10` y este plan; comprobar que rama de trabajo nace de `main` actualizado.
- [ ] Confirmar **caracteristicas del 2N2222 real** y su encapsulado/pinout; revisar materiales: resistencias, protoboard o PCB, multimetro, cables; documentar lo que falta.
- [ ] Identificar electrica o documentalmente la red OE pull-down y version exacta del breakout; definir resistor pull-up y transistor, justificar VIH y VOL a 3.3 V (con margen).
- [ ] Elegir un GPIO libre J6 por pinout oficial Jetson Nano 2GB, comprobar mux y estados por defecto **sin cambiar pines usados para I2C ni power**.
- [ ] Definir circuito independiente de timeout/interlock, manejo de perdida de control y corte fisico; dimensionar protecciones y enclavamientos.

### Fase B. Desarrollo y pruebas sin actuacion fisica

- [ ] Escribir especificacion y pruebas de maquina de estados Python 3.6 con transporte falso (mock I2C y GPIO).
- [ ] Probar 1 canal y 15 FULL OFF, default OFF, fallo por timeout, reinicio, secuencia de autorizacion, perdida de enlace, comandos invalidos y latch de FAULT.
- [ ] Ejecutar pruebas en la Mac y en la Jetson con `OE` aun fijo HIGH; sin requerir cambio fisico de cableado.
- [ ] Revisar por pares el esquema definitivo y el interlock; nunca habilitar un pin sin validar su correspondencia fisica.

### Fase C. Ensayo electrico sin movimiento

- [ ] Cortar STOP, apagar Jetson por sistema, desconectar las alimentaciones y verificar ausencia de tension/residuales antes de modificar OE; no tocar bornes de AC.
- [ ] Construir el circuito de control en banco con medicion, asegurando OE HIGH **en ausencia de orden**, incluso durante arranque, cable desconectado, reset de Linux y timeout hardware.
- [ ] Verificar primero que GPIO no lucha contra el riel J6 3.3 V, que el transistor conmuta correctamante y que la resistencia pull-up supera el pull-down integrado.
- [ ] Probar con osciloscopio/analizador cuando sea viable la forma de onda del **unico canal permitido**, con el STOP activado y sin fuerza en motores; medir LOW de OE y HIGH/LOW con margen.
- [ ] Verificar al menos 3 veces que falla a estado inhibido ante reset/reboot, error I2C, desconexion de cable y vencimiento del watchdog externo.

### Fase D. Primera prueba fisica de la garra acoplada (SOLO tras superar A–C)

- [ ] Despejar la garra, no sujetar objeto y comprobar que no hay pellizcos ni topes proximos; asegurar el brazo frente a caidas cuando se retire potencia.
- [ ] Validar direccion, recorrido efectivo, posicion fisica inicial y pulso seguro de inicio con el mecanismo **ya montado**; si no hay forma segura de determinarlo, suspender movimiento y replantear la prueba.
- [ ] Operador junto al paro, nadie dentro de la zona de movimiento, un solo servo autorizado con ventana corta y supervision de corriente/temperatura.
- [ ] Primer movimiento de amplitud verdaderamente minima **despues de calibracion**, nunca iniciar con `Home` ni energizar con salida PWM preprogramada a un angulo arbitrario.
- [ ] Registrar observaciones, abortar ante zumbido fuerte, tope, tiron, reinicios, sobrecalentamiento, deformaciones o fallo de comunicacion.
- [ ] Volver a DISARMED sin enviar Home, inhibir OE, comprobar FULL OFF 16/16 y cortar potencia antes de abandonar el banco.

### Fase E. Ampliacion gradual

- [ ] Repetir calibracion y pruebas de cada SG90/MG995 uno por uno, considerar gravedad/cargas crecientes, limites mecánicos, fuente y picos reales.
- [ ] Integrar control de Jetson en backend/UI solo tras validar interfaz de seguridad, autenticacion, acciones permitidas y desacople del modo replay.
- [ ] Mantener prohibido el control autonomo por IA y secuencias `saludo/rutina` hasta completar validacion de seis ejes y seguridad independiente.

## 6. Criterios de aceptacion antes del primer pulso fisico

**Todos obligatorios:**

1. Esquema de transistor, pull-up, base y hardware watchdog revisado y montado sin cables sueltos, sin corto de GPIO al pin17.
2. OE HIGH estable con modo seguro, reboot, GPIO hi-Z y watchdog vencido; voltajes **medidos**, no deducidos.
3. Solo canal 5 permitido, 15 x FULL OFF y guardas contra escritura accidental o `home` global.
4. Fuente AC/STOP seguros y con corte comprobado; la logica Jetson separada y la zona de alcance despejada.
5. Calibracion de posicion fisica inicial, direccion, topes de garra, pulsos validos del SG90 particular y brazo asegurado.
6. Test unitarios y de fallos pasados, operador presente con capacidad de abortar y no armado automatico tras perdida de energia.

**Si cualquiera falla, el resultado correcto es NO MOVER EL BRAZO.**

## 7. Cierre de sesion y comandos de apagado

**Orden obligatorio al apagar:** activar primero STOP para quitar alimentacion AC a fuente de 5 V; comprobar V+ sin potencia, mantener OE alto mientras Jetson siga encendida. Despues ejecutar desde Mac:

```bash
ssh -t -o ConnectTimeout=10 antonio@jetson-nano.local 'sudo shutdown -h now'
```

Esperar cierre de SSH y apagado de Jetson; desconectar su eliminador solo cuando termino. **Nunca dejar la potencia de servos activa con Jetson apagada**, porque desaparecera VCC 3.3 V y el nivel de OE no esta garantizado. No cambiar conexiones esta noche.

**Siguiente sesion:** actualizar `main` local y crear rama nueva desde el ultimo merge. Hacer primero Fase A del plan, no ejecutar el modo `hardware`.

## 8. Fuentes del diseño y documentacion previa

- NXP PCA9685, hoja de datos (seccion 7.4 OE activo LOW, seccion 12 umbrales VIH >= 0.7 VDD): https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf
- Adafruit, pinouts de placa 16 canales (OE pulled LOW by default, diferencia VCC y V+): https://learn.adafruit.com/16-channel-pwm-servo-driver/pinouts
- NVIDIA Jetson.GPIO (numeracion, configuracion y libreria): https://github.com/NVIDIA/jetson-gpio
- Cableado y limites: [01-hardware-y-conexiones.md](01-hardware-y-conexiones.md)
- PCA9685 I2C y FULL OFF: [08-jetson-pca9685-i2c-pruebas.md](08-jetson-pca9685-i2c-pruebas.md)
- Simulador seis ejes: [09-jetson-simulacion-seis-servos.md](09-jetson-simulacion-seis-servos.md)
- Registro de fuente, mediciones, STOP y foto: [10-seguridad-fuente-servos-5v-10a.md](10-seguridad-fuente-servos-5v-10a.md)

**Este documento es un plan de trabajo, no una indicacion de manipular circuitos de red ni de habilitar los servos sin supervision y pruebas.**


## 9. Decision de componente: 2N2222 metalico TO-18 (31 de octubre de 2026)

**Decision confirmada por el usuario:** dispone de versiones TO-92 (plasticos) y TO-18 (metalicos, 'de latita') y **prefiere utilizar los TO-18** para el circuito de habilitacion OE. Adoptar **2N2222 / 2N2222A de encapsulado metalico TO-18** como candidato de diseño, en lugar de TO-92, sin alterar los requisitos de watchdog e inhibicion por defecto.

**Referencia de fabricante, NO identificacion de la pieza concreta del usuario:** Philips/NXP describe los 2N2222 y 2N2222A TO-18 con emisor=pin 1, base=pin 2, colector=pin 3 y **carcasa metalica unida al colector**. La numeracion debe orientarse por la muesca y la vista exacta del dibujo del datasheet; no es seguro suponer que la disposicion del plastico TO-92 es igual. Fuente: https://web.stanford.edu/class/ee133/datasheets/2n2222.pdf (Philips Semiconductors, pagina impresa 2, figura 1).

**Implicaciones de diseño:**

- El encapsulado metalico **no se conecta a V+ 5V ni transporta corriente de motores**. El 2N2222 controla solamente el nodo OE de logica 3.3V por medio de un circuito de colector abierto con resistencias, luego de aprobar el esquema.
- En la version TO-18 de Philips el **colector esta unido a la carcasa**, por lo que la latita puede ser un punto electrico activo; evitar contacto con chasis, GND, disipadores, otras piezas metalicas o conductores sin aislamiento. Confirmar si esto es asi para el fabricante exacto del usuario.
- **Antes de elegir pines o soldar:** solicitar foto nitida de un transistor real donde se vea el texto grabado en su lata y, de ser posible, una segunda vista de la base con las tres patillas y su muesca. Contrastar la inscripcion con la hoja de datos del mismo fabricante; usar multimetro en modo diodo para corroborar polaridad E/B/C si es necesario.
- No hacer cambios a OE ni alimentar motores por este cambio de preferencia. La conexion actual OE a J6 pin fisico 17 (3.3V fijo) sigue vigente y debe permanecer sin tocar.

**Siguiente paso practico:** identificar marcaje y muesca del componente exacto; despues dimensionar resistencias y definir el circuito con la red pull-down de OE y un interlock independiente.


## 10. Inventario fotografico: cuatro 2N2222A metalicos disponibles (31 de octubre de 2026)

El usuario envio **cuatro fotografias de uno de sus transistores** y confirmo: «Tengo 4 de estos». El componente de las fotos es de encapsulado metalico con tres terminales, formato compatible con TO-18. La inscripcion visible es **compatible con `2N2222A`** (parte de la palabra/modelo se curva alrededor de la lata); se aprecia logotipo circular, pero **el fabricante y lote no pueden verificarse con certeza** por las fotos. El usuario dispone de **4 piezas** de este tipo, no necesariamente cada una caracterizada individualmente.

**Fuente de comparacion**: hoja oficial onsemi 2N2222A (`https://www.onsemi.com/download/data-sheet/pdf/2n2222a-d.pdf`), paquete TO-18 / CASE 206AA / STYLE 1. Dibujo visto desde abajo con muesca de orientacion y pines `1=emisor`, `2=base`, `3=colector`; NXP/Philips documenta para su version que la carcasa metalica esta unida al colector (`https://web.stanford.edu/class/ee133/datasheets/2n2222.pdf`). El dibujo es **referencia de un fabricante y no identifica por si solo el pinout exacto de la pieza fotografiada**.

**No se ve de frente la cara inferior de la lata ni la muesca de alineacion con suficiente claridad**; no asignar a las patillas de la imagen C/B/E por su ubicacion aparente. Preferir prueba externa del componente suelto en modo diodo de multimetro, antes de introducirlo en protoboard o soldarlo, especialmente por la posibilidad de que la carcasa sea colector.

**Paso propuesto 11.2 (sin cables de Jetson):** una pieza desconectada, multimetro en modo prueba de diodos; identificar el terminal de base NPN encontrando ~0.5-0.8 V desde punta roja en base hacia cada una de las otras dos patillas con punta negra, y lectura OL al invertir polaridad. Anotar combinaciones y luego contrastar colector/emisor con muesca y/o diagrama del fabricante exacto; **el modo diodo por si solo no determina siempre de forma fiable que patilla es C frente a E**. No hacer prueba en un circuito energizado. Si no hay dos lecturas directas de diodo, no usar esa unidad.

**Inventario para el circuito:** reservar 1 unidad 2N2222A TO-18 para el futuro sink OE, 3 unidades de repuesto; las resistencias, componentes de watchdog independiente y montaje final siguen por identificar. El resto de requisitos del plan siguen vigentes: NO cambiar el enlace directo OE–3.3 V todavía, NO conectar GPIO directo y NO habilitar servos.


## 11. Paso 11.2 informado: terminales identificados por el usuario (2 de noviembre de 2026)

El usuario confirma que **ya identifico cual terminal es emisor, base y colector** de su transistor metalico TO-18. No proporciono lecturas numericas de multimetro ni dibujo orientado; registrar como confirmacion del usuario, **sin inferir orientacion fisica propia ni dar por verificado el pinout de fabricante**.

### Proposito del 2N2222 en el proyecto

- Un 2N2222 (NPN) se utilizara exclusivamente para **hundir a GND el pin OE** del PCA9685 mediante una etapa de colector abierto, y solo cuando una logica de permiso adecuadamente supervisada lo autorice; nunca para conducir potencia de los servos.
- Con el transistor **cortado**, un pull-up externo bien dimensionado mantiene `OE` cerca de 3.3 V, inhibiendo las salidas incluso si Jetson.GPIO no configura una salida. El pull-down de la placa debe verificarse para que el nivel HIGH sea valido.
- Con el transistor en conduccion, OE podria estar LOW, pero **solo** se habilitarian los canales que no esten en FULL OFF; el primer candidato es canal 5 de garra, sin permiso sobre los demas.
- **No basta con un GPIO + 2N2222** para cubrir congelacion del sistema: se mantiene como requisito un watchdog/interlock de hardware independiente para impedir habilitacion prolongada en ausencia de heartbeat.
- La fuente de potencia de servos se sigue cortando con el STOP fisico independiente en el lado de entrada AC; no sustituirlo por el transistor.

### Siguiente comprobacion (sin modificar cableado)

Levantar inventario de **resistencias disponibles y sus valores**, protoboard, jumpers y multimetro. Valores **candidatos de estudio, NO autorizados para montar aun**: 1 kOhm para pull-up de OE (sujeto a caracterizacion de pull-down de placa y VIH), 4.7 kOhm para la base y 47 kOhm para pull-down de base; deben revisarse mediante calculo/medicion y complementarse con el interlock independiente. Si se desconoce el inventario, pedir foto o codigo de colores de las resistencias.

**Prohibicion vigente:** NO conectar ni retirar OE de J6 pin fisico 17 (3.3 V) con algun equipo energizado, NO conectar un GPIO activo a esa conexion, NO habilitar PWM fisico, NO mover el brazo. No presumir que los rangos logicos documentados son posiciones calibradas del mecanismo.


## 12. Ruta alternativa de prueba directa sin transistores (2 de noviembre de 2026)

**Nueva preferencia del usuario:** «mi RECOEMECNADACION ES QUE YA DE UNA VEZ LE MANDEMOS LAS señales apra que eno neceitmeos ningun circuito adicional». Para **una prueba manual supervisada del canal 5 de la garra**, es posible prescindir inicialmente del 2N2222 y manejar la placa por I2C directamente; se conserva este plan con transistor/watchdog como ruta a largo plazo.

**Avance implementado en la rama:** `jetson/pca9685_safe.py` incorpora la accion `stage-garra-1500 --confirm-stop-oe`: programa 1500 microsegundos en registros del canal 5 **enmascarados por FULL OFF**, valida FULL OFF 16/16 y nunca cambia OE ni habilita PWM. Es una escritura I2C real, **no movimiento**; las pruebas `jetson/tests/test_pca9685_safe.py` cubren rechazo y modo seguro.

El primer movimiento real exigiria modificar posteriormente la conexion de OE (hoy fija HIGH en pin17) para gobernarla desde un GPIO de 3.3 V identificado, nunca ambos a la vez, con Jetson y fuente completamente apagadas. Con GPIO directo sin watchdog el estado durante boot/crash puede permitir salidas: **NO autoriza autonomia, control sin supervisión, ni presupone fallo seguro**. El STOP fisico permanece activo en la fase de programacion y accesible durante futuras pruebas.

**Procedimiento y condiciones de la ruta sin transistor:** [12-prueba-directa-pca9685-sin-transistor.md](12-prueba-directa-pca9685-sin-transistor.md). No instalar el 2N2222 por ahora ni modificar los seis conectores de servos.
