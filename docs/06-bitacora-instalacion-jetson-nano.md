# Bitácora de instalación — NVIDIA Jetson Nano 2GB

**Proyecto:** Brazo Robot / laboratorio de IA física  
**Fecha de corte:** 26 de octubre de 2026  
**Equipo:** NVIDIA Jetson Nano 2GB Developer Kit (modelo original; no Jetson Orin)  
**Usuario Linux:** antonio  
**Hostname:** jetson-nano  
**Estado:** instalación base verificada; aún no se ha conectado el brazo ni ejecutado el software de percepción en esta Jetson.

> Documento de continuidad basado en comandos y salidas observados durante la instalación. Distingue hechos comprobados de decisiones y trabajo pendiente. No contiene contraseñas ni tokens. Para el estado del proyecto y los siguientes pasos, consultar [07-estado-y-continuidad-del-proyecto.md](07-estado-y-continuidad-del-proyecto.md).

## 1. Objetivo de la instalación

Preparar la Jetson Nano 2GB para aportar visión artificial, procesamiento acelerado con NVIDIA y, tras diseñar una capa segura, integración con el brazo robótico de seis ejes. El programa de control moderno y la interfaz 3D del repositorio se ejecutarán inicialmente en un equipo anfitrión compatible (Mac); no se sustituirá a ciegas el Python de JetPack.

**Criterio de conservación:** evitar reinstalaciones innecesarias, no cambiar el Python del sistema, no actualizar globalmente todos los paquetes y no comprometer CUDA/TensorRT/cuDNN.

## 2. Medio de instalación y grabación de la microSD

| Elemento | Registro |
|---|---|
| Imagen oficial seleccionada | JetPack 4.6.1 para Jetson Nano 2GB |
| Archivo en la Mac | ~/Downloads/jetson-nano-2gb-jp461-sd-card-image.zip |
| MD5 del ZIP verificado | f862a729f0bd9d4a3be52c32a3bc9f2a |
| Tamaño de descarga informado | Aproximadamente 6.1 GB |
| microSD identificada en la Mac | /dev/disk4, aproximadamente 62.2 GB (identificador temporal) |
| Herramienta definitiva | balenaEtcher; grabación y verificación concluidas |
| Partición de aplicación seleccionada en primer arranque | 59,329 MB |

**Cronología:**

1. Primero se intentó grabar la imagen con Raspberry Pi Imager; no se consiguió completar correctamente el proceso de configuración inicial.
2. Se comprobó que el archivo ZIP correspondía a la imagen de NVIDIA y se verificó el hash MD5.
3. Se volvió a grabar la microSD con balenaEtcher, con verificación correcta.
4. En un arranque apareció un bloqueo transitorio de debconf (config.dat locked by another process). Se resolvió mediante un ciclo de apagado/encendido; no fue necesario modificar manualmente las bases de datos de paquetes.
5. El dispositivo inició el asistente de primera configuración.

**Precaución para recuperación:** /dev/disk4 es el identificador observado *en aquella ocasión*. Nunca copiarlo como destino de flasheo sin confirmar de nuevo el disco: la grabación borra la unidad elegida.

## 3. Acceso a la consola y configuración inicial

La instalación inicial se completó desde la Mac mediante la consola serie USB de la Jetson, usando su puerto micro-USB de datos.

- Dispositivo serie observado en macOS: /dev/cu.usbmodem14243200310403 (puede cambiar).
- Conexión utilizada:

~~~bash
sudo screen /dev/cu.usbmodem14243200310403 115200
~~~

En el asistente de primer arranque se configuró:

| Parámetro | Valor / elección |
|---|---|
| Nombre completo | Antonio Richaud |
| Usuario | antonio |
| Nombre del equipo | jetson-nano |
| Idioma/locale | Español |
| Zona horaria | México, Ciudad de México |
| Reloj de hardware | UTC |
| Partición de aplicaciones | máximo disponible, 59,329 MB |
| Swap solicitado en el asistente | Archivo de 4 GB |
| Conexión primaria | eth0, cable Ethernet |
| Modo de potencia seleccionado | MAXN |

La contraseña fue establecida por el usuario y **no está registrada** en este documento.

El indicador de consola tras el inicio de sesión fue: antonio@jetson-nano:~$.

## 4. Red Ethernet, Internet, mDNS y SSH

**Red observada durante la configuración:**

| Parámetro | Resultado |
|---|---|
| Interfaz | eth0 |
| Dirección DHCP observada | 192.168.100.60/24 |
| Puerta de enlace | 192.168.100.1 |
| Router | Huawei OptiXstar HG8145X6-12 (Megacable) |
| Conexión física | LAN1 del router (antes se había probado LAN4) |
| Enlace Ethernet observado | 100 Mb/s |
| Equipo cliente Mac en una prueba | 192.168.100.35 |
| Host mDNS probado | jetson-nano.local |
| SSH sin conexión USB | **Probado correctamente** |
| Acceso a GitHub | Ping completado, 3 de 3 respuestas |

La dirección 192.168.100.60 fue entregada por DHCP y **no debe tratarse como fija**. La sesión de administración del router disponible no permitió configurar una reserva DHCP; por ello se probó y adoptó el acceso por mDNS, que funcionó desde la Mac.

Comandos empleados y/o verificados:

~~~bash
# En la Mac, en la misma red local:
ping -c 3 jetson-nano.local
ssh antonio@jetson-nano.local

# Alternativa usando la IP observada (podría cambiar):
ssh antonio@192.168.100.60

# Ya dentro de la Jetson:
hostname
whoami
uptime
~~~

Se comprobó expresamente que el SSH seguía funcionando **después de retirar el cable micro-USB**. La Jetson quedó administrable por Ethernet.

Se observó esta huella ED25519 del servidor SSH al establecer la confianza desde la Mac: SHA256:VifVij8CTDXCpxgwQTKWL0odxRa3NP9A5LvPm/ohbh0. Si cambia, verificar el motivo directamente en la máquina antes de aceptar una nueva huella.

**Aviso de seguridad:** el servidor SSH antiguo emitió una advertencia de intercambio de claves sin mecanismos poscuánticos. No impidió la conexión; debe evitarse exponer este equipo directamente a Internet. Los servicios WebSocket de prueba tampoco deben publicarse sin autenticación y restricciones de red.

## 5. Sistema operativo y recursos comprobados

| Componente | Evidencia observada |
|---|---|
| JetPack | Imagen 4.6.1 |
| Ubuntu | 18.04.6 LTS / Bionic (ARM64) |
| L4T | R32.7.1 |
| Paquete NVIDIA básico | nvidia-l4t-core 32.7.1-20220219090432 |
| Kernel | 4.9.253-tegra |
| Git | 2.17.1 |
| Python del sistema | 3.6.9 |
| RAM física | 1.9 GiB |
| Swap total observado | 5.0 GiB |
| Swap en archivo | /swapfile, 4 GiB |
| zram | /dev/zram0 a /dev/zram3, aproximadamente 247.5 MiB cada uno |
| Almacenamiento raíz | /dev/mmcblk0p1, 57 GiB |
| Uso observado de raíz | 16 GiB usados, 39 GiB disponibles, 29% de ocupación |

Estos son **valores de la sesión de verificación**, no promesas sobre la memoria o el espacio disponible en sesiones futuras.

Comandos de diagnóstico no destructivos:

~~~bash
cat /etc/nv_tegra_release
uname -r
git --version
python3 --version
free -h
swapon --show
df -h /
dpkg-query -W nvidia-l4t-core 2>/dev/null
~~~

La lectura de /etc/nv_tegra_release mostró:

~~~text
# R32 (release), REVISION: 7.1, GCID: 29818004, BOARD: t210ref, EABI: aarch64, DATE: Sat Feb 19 17:05:08 UTC 2022
~~~

Se consultó el metapaquete nvidia-jetpack, que no figuró como instalado. **Eso no basta para concluir que falten las bibliotecas de NVIDIA:** CUDA, TensorRT y cuDNN se comprobaron individualmente.

## 6. Componentes NVIDIA y visión comprobados

| Componente | Versión | Cómo se validó |
|---|---|---|
| CUDA Toolkit / nvcc | 10.2.300 | /usr/local/cuda/bin/nvcc --version |
| cuDNN lib | libcudnn8 8.2.1.32-1+cuda10.2 | dpkg-query |
| TensorRT lib | libnvinfer8 8.2.1-1+cuda10.2 | dpkg-query |
| Bindings Python TensorRT | python3-libnvinfer 8.2.1-1+cuda10.2 | dpkg-query |
| API TensorRT en Python | 8.2.1.8 | import tensorrt; versión |
| OpenCV en Python | 4.1.1 | import cv2; versión |

Comprobaciones seguras:

~~~bash
/usr/local/cuda/bin/nvcc --version
dpkg-query -W libcudnn8 libnvinfer8 python3-libnvinfer 2>/dev/null
python3 -c "import cv2; print(cv2.__version__)"
python3 -c "import tensorrt; print(tensorrt.__version__)"
~~~

**Alcance real de la prueba:** las bibliotecas están presentes e importan correctamente; aún **no** se ha hecho una inferencia real con TensorRT, procesamiento GPU de una cámara o benchmark de rendimiento.

## 7. Problema inicial con APT y su resolución

Al principio, Python 3.6.9 funcionaba, pero:

- python3 -m pip --version devolvía No module named pip.
- python3-pip no estaba localizado en el caché de APT.
- python3-venv y python3.6-venv figuraban sin candidato.
- /var/lib/apt/lists tenía 13 archivos regulares en el primer diagnóstico.

Se inspeccionaron las fuentes sin modificarlas. Ya existían:

- Ubuntu ARM64 en http://ports.ubuntu.com/ubuntu-ports/: bionic, bionic-updates, bionic-security y bionic-backports; componentes main, restricted, universe y multiverse.
- NVIDIA Jetson: https://repo.download.nvidia.com/jetson/common y /jetson/t210, suite r32.7.
- Repositorios locales para CUDA 10.2 y VisionWorks.

**Solución aplicada:**

~~~bash
sudo apt update
~~~

Descargó 42.9 MB de índices y terminó sin errores. Mostró 348 paquetes actualizables. **No se ejecutó apt upgrade ni full-upgrade**.

Después de refrescar el caché se encontraron los candidatos:

| Paquete | Versión candidata observada |
|---|---|
| python3-pip | 9.0.1-2.3~ubuntu1.18.04.8 |
| python3-venv | 3.6.7-1~18.04 |
| python3.6-venv | 3.6.9-1~18.04ubuntu1.12 |

Primero se realizó una simulación:

~~~bash
sudo apt-get -s install --no-install-recommends \
  python3-pip \
  python3-venv \
  python3.6-venv
~~~

Resultado: **4 paquetes nuevos, 5 actualizados, 0 eliminados y 343 pendientes**. Los cinco actualizados eran componentes de Python 3.6 (libpython3.6, libpython3.6-minimal, libpython3.6-stdlib, python3.6 y python3.6-minimal), de la revisión ubuntu1.6 a ubuntu1.12. No se propusieron cambios a los paquetes NVIDIA.

Instalación efectivamente realizada:

~~~bash
sudo apt-get install --no-install-recommends \
  python3-pip \
  python3-venv \
  python3.6-venv
~~~

Se completó sin errores. El aviso debconf: delaying package configuration, since apt-utils is not installed fue informativo, no un fallo. La actualización mantuvo Python **3.6.9** y se verificó de nuevo la importación de OpenCV 4.1.1 y TensorRT 8.2.1.8.

**Regla permanente:** no ejecutar un apt upgrade masivo para resolver problemas aislados; simular primero y revisar si toca paquetes NVIDIA o el Python del sistema.

## 8. Entorno virtual NVIDIA funcional

Carpeta de trabajo creada:

~~~bash
mkdir -p ~/robot-lab
~~~

Entorno creado y activado:

~~~bash
python3 -m venv --system-site-packages ~/robot-lab/.venv-jetson
source ~/robot-lab/.venv-jetson/bin/activate
~~~

Se eligió --system-site-packages **deliberadamente** para acceder a cv2 y tensorrt instalados por el sistema. Por ello, el entorno no está aislado al cien por ciento: ve paquetes globales, aunque sus instalaciones locales residen dentro de ~/robot-lab/.venv-jetson.

Verificaciones realizadas y correctas:

~~~bash
which python
# /home/antonio/robot-lab/.venv-jetson/bin/python

python -c "import cv2, tensorrt; print('OpenCV:', cv2.__version__); print('TensorRT:', tensorrt.__version__)"
# OpenCV: 4.1.1
# TensorRT: 8.2.1.8
~~~

pip comenzó en 9.0.1. **Solo dentro del entorno virtual**, se ejecutó:

~~~bash
python -m pip install --upgrade "pip==21.3.1"
python -m pip --version
~~~

Salida final:

~~~text
pip 21.3.1 from /home/antonio/robot-lab/.venv-jetson/lib/python3.6/site-packages/pip (python 3.6)
~~~

Se volvieron a importar cv2 4.1.1 y tensorrt 8.2.1.8, ambos correctamente.

**Al terminar:** se salió del entorno con deactivate para empezar a preparar el repositorio. Activarlo cuando se requiera con:

~~~bash
source ~/robot-lab/.venv-jetson/bin/activate
~~~

**No ejecutar** pip install --upgrade pip sin fijar versión, y **no** ejecutar sudo pip. Mantener el pip global de Ubuntu gestionado por APT.

## 9. Repositorio GitHub clonado y rama Jetson

Repositorio: https://github.com/Antonio-Richaud/Brazo-robot  
Ruta: /home/antonio/robot-lab/Brazo-robot  
Rama principal original: main  
Commit original observado: 8251aa902c04192c4e1d8ed143515d59bfdd7f7a

Secuencia efectivamente realizada en la Jetson:

~~~bash
deactivate # Solo si el venv estaba activo
cd ~/robot-lab
git clone https://github.com/Antonio-Richaud/Brazo-robot.git
cd Brazo-robot
git status -sb
git log -1 --oneline
~~~

El primer estado fue main...origin/main, limpio, commit 8251aa9.

La rama **feat/jetson-nano-physical-ai** se creó remotamente en GitHub desde ese commit, sin cambiar main, y luego se configuró en la Jetson con:

~~~bash
git fetch origin
git checkout -b feat/jetson-nano-physical-ai \
  --track origin/feat/jetson-nano-physical-ai
git status -sb
~~~

Salida observada:

~~~text
## feat/jetson-nano-physical-ai...origin/feat/jetson-nano-physical-ai
~~~

Git en esta Jetson es 2.17.1: utilizar git checkout en vez de git switch.

**Importante para próximas sesiones:** cuando se añada documentación o código en GitHub desde otro dispositivo, ejecutar en la Jetson:

~~~bash
cd ~/robot-lab/Brazo-robot
git pull --ff-only origin feat/jetson-nano-physical-ai
~~~

No volver a clonar encima de la carpeta existente.

## 10. Foto exacta del estado al cierre

**Ya funciona / fue observado:**

- Imagen NVIDIA correcta y microSD grabada con verificación.
- Arranque inicial, usuario antonio y acceso mediante SSH.
- mDNS jetson-nano.local desde la Mac y Ethernet independiente del USB.
- JetPack/L4T, CUDA, cuDNN, TensorRT y OpenCV presentes.
- Python 3.6, pip en APT y entorno virtual NVIDIA con pip 21.3.1.
- Repositorio clonado; rama Jetson local y remota correctamente enlazadas.

**Todavía NO se hizo:**

- Instalar o probar pyrealsense2/librealsense en Jetson.
- Conectar o comprobar la D435i por USB 3 en la Jetson.
- Ejecutar jetson_perception_node.py en Jetson.
- Instalar el backend moderno con requirements.txt en Jetson.
- Ejecutar pruebas de backend o frontend en la Jetson.
- Conectar PCA9685 por I2C, alimentar servos o mover el brazo desde Jetson.
- Implementar o desplegar control físico directo desde Jetson.
- Instalar modelos de IA, efectuar inferencia GPU, calibrar la cámara o habilitar autonomía.

El hecho de que una dependencia o un módulo exista en GitHub **no significa** que ya se haya ejecutado en la Jetson. El nodo de percepción actual tiene incompatibilidades de sintaxis/API con Python 3.6; ver el documento de continuidad.

## 11. Diagnóstico rápido para una nueva sesión

Sin alterar la instalación:

~~~bash
# Mac conectada a la misma red:
ssh antonio@jetson-nano.local

# Dentro de la Jetson:
hostname
whoami
cat /etc/nv_tegra_release
python3 --version
/usr/local/cuda/bin/nvcc --version
free -h
swapon --show
df -h /

# Entorno NVIDIA:
source ~/robot-lab/.venv-jetson/bin/activate
python -m pip --version
python -c "import cv2, tensorrt; print(cv2.__version__, tensorrt.__version__)"
deactivate

# Repositorio:
cd ~/robot-lab/Brazo-robot
git status -sb
git log -1 --oneline
~~~

Resultados de referencia: Python 3.6.9; pip en venv 21.3.1; OpenCV 4.1.1; TensorRT 8.2.1.8; rama feat/jetson-nano-physical-ai. Si alguna verificación falla en el futuro, diagnosticar antes de reinstalar.

## 12. Recuperación y seguridad operacional

- Si cambia la IP DHCP, usar jetson-nano.local desde la misma LAN; si mDNS falla, consultar el DHCP del router antes de configurar una IP estática.
- Si SSH no conecta, verificar energía, Ethernet, DHCP y, solo si hace falta, volver a acceder por consola micro-USB. El nombre del dispositivo serie puede cambiar.
- Si falta pip dentro del entorno, comprobar primero la activación con which python; no sustituir /usr/bin/python3.
- Si APT deja de resolver paquetes, comprobar las fuentes e índices antes de editar repositorios o reinstalar.
- La partición raíz está en la microSD; mantener copias del código en GitHub y respaldos separados de calibraciones locales y configuraciones que no deban publicarse.
- No publicar contraseñas, claves privadas, tokens, información de redes externas ni ficheros .env en el repositorio.
- No dar potencia a servos por el hecho de que Linux arranque; el movimiento físico requiere una etapa explícita de validación y corte de energía.
- La base Ubuntu 18.04/JetPack 4.x es antigua; no publicar servicios SSH/WebSocket hacia Internet.

## 13. Documentación relacionada

- [01 — Hardware y conexiones](01-hardware-y-conexiones.md)
- [02 — Firmware ESP32](02-firmware-esp32.md)
- [03 — Control Center](03-control-center.md)
- [04 — RealSense + Jetson (diseño, no despliegue verificado)](04-realsense-jetson.md)
- [05 — Manual de uso y pruebas](05-manual-de-uso-y-pruebas.md)
- [07 — Estado del proyecto, decisiones y siguientes pasos](07-estado-y-continuidad-del-proyecto.md)
