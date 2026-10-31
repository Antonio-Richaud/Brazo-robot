#!/usr/bin/env python3
"""Inspeccion y bloqueo preventivo del PCA9685 en Jetson Nano 2GB.

Compatible con Python 3.6 y con i2c-tools de JetPack 4.6.1.
NO tiene ninguna funcion para habilitar canales o mover motores.

Conexiones logicas previstas: J6 pin 1 -> VCC 3.3 V,
J6 pin 3 -> SDA, J6 pin 5 -> SCL, J6 pin 6 -> GND,
J6 pin 17 -> OE 3.3 V (salidas inhibidas).
Mantener V+ (alimentacion de motores) desconectado.
"""

import argparse
import subprocess
import sys


MODE1 = 0x00
MODE2 = 0x01
LED0_ON_L = 0x06
ALL_LED_OFF_H = 0xFD
PRE_SCALE = 0xFE
FULL_OFF = 0x10
CHANNEL_COUNT = 16
ROBOT_CHANNEL_COUNT = 6
EXPECTED_PRE_SCALE = 0x79  # 25 MHz nominal, aproximadamente 50 Hz


def channel_off_high_register(channel):
    if not isinstance(channel, int) or not 0 <= channel < CHANNEL_COUNT:
        raise ValueError("Canal PCA9685 fuera de rango: 0..15")
    return LED0_ON_L + 4 * channel + 3


class I2CToolsBus(object):
    """Transporte de diagnostico con herramientas ya presentes en la Jetson.

    No es un transporte para lazos de control de servos en tiempo real.
    Solo utiliza la direccion especificada del bus especificado.
    """

    def __init__(self, bus_number=1, address=0x40, runner=None):
        if bus_number != 1 or address != 0x40:
            raise ValueError("Solo se permite /dev/i2c-1 y 0x40 en esta fase")
        self.bus_number = bus_number
        self.address = address
        self._runner = runner or self._run

    @staticmethod
    def _run(argv):
        result = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=5,
            check=True,
        )
        return result.stdout.strip()

    @staticmethod
    def _check_byte(value):
        if not isinstance(value, int) or not 0 <= value <= 255:
            raise ValueError("Registro/valor debe ser un byte (0..255)")

    def read_reg(self, register):
        self._check_byte(register)
        output = self._runner([
            "i2cget", "-y", str(self.bus_number), hex(self.address),
            hex(register), "b",
        ])
        return int(output.strip(), 16)

    def write_reg(self, register, value):
        self._check_byte(register)
        self._check_byte(value)
        self._runner([
            "i2cset", "-y", str(self.bus_number), hex(self.address),
            hex(register), hex(value), "b",
        ])


class SafePCA9685(object):
    """Inspecciona y permite aplicar FULL OFF, pero JAMAS armar salidas.

    Importante: por I2C no se puede comprobar si OE esta realmente en alto.
    OE debe mantenerse unido fisicamente a VCC de 3.3 V en esta fase.
    """

    def __init__(self, bus):
        self.bus = bus

    def all_channels_off(self):
        return all(
            self.bus.read_reg(channel_off_high_register(channel)) & FULL_OFF
            for channel in range(CHANNEL_COUNT)
        )

    def inspect(self):
        mode1 = self.bus.read_reg(MODE1)
        mode2 = self.bus.read_reg(MODE2)
        pre_scale = self.bus.read_reg(PRE_SCALE)
        off_channels = [
            channel for channel in range(CHANNEL_COUNT)
            if self.bus.read_reg(channel_off_high_register(channel)) & FULL_OFF
        ]
        return {
            "mode1": mode1,
            "mode2": mode2,
            "pre_scale": pre_scale,
            "off_channels": off_channels,
            "all_off": len(off_channels) == CHANNEL_COUNT,
        }

    def disable_all(self):
        """Aplica el corte logico global FULL OFF (NO es paro de emergencia)."""
        self.bus.write_reg(ALL_LED_OFF_H, FULL_OFF)
        if not self.all_channels_off():
            raise RuntimeError("No se pudo verificar FULL OFF en los 16 canales")

    def stage_disabled_pulse(self, channel, pulse_us):
        """Escribe un pulso ENMASCARADO por FULL OFF; nunca lo habilita.

        Intencionadamente no se expone como accion del CLI en esta fase.
        Limitado a los seis canales del brazo, 1000..2000 us de laboratorio.
        Estos valores no implican calibracion ni son un rango seguro de servo.
        """
        if not isinstance(channel, int) or not 0 <= channel < ROBOT_CHANNEL_COUNT:
            raise ValueError("Solo se permite preparar canales 0..5")
        if not isinstance(pulse_us, int) or not 1000 <= pulse_us <= 2000:
            raise ValueError("Pulso de laboratorio fuera de 1000..2000 us")
        if self.bus.read_reg(PRE_SCALE) != EXPECTED_PRE_SCALE:
            raise RuntimeError("PRE_SCALE no coincide con 0x79; revisar frecuencia")
        if not self.all_channels_off():
            raise RuntimeError("Se rechazo preparar PWM: existe un canal habilitado")

        # f_pwm = 25 MHz / (4096 * (prescale + 1)).
        # Cuentas de pulso = microsegundos * 25 / (prescale + 1).
        count = int(round(pulse_us * 25.0 / (EXPECTED_PRE_SCALE + 1)))
        base = LED0_ON_L + 4 * channel
        # Asegurar FULL OFF incluso si falla una escritura posterior.
        self.bus.write_reg(base + 3, FULL_OFF)
        self.bus.write_reg(base + 0, 0x00)
        self.bus.write_reg(base + 1, 0x00)
        self.bus.write_reg(base + 2, count & 0xFF)
        self.bus.write_reg(base + 3, FULL_OFF | ((count >> 8) & 0x0F))
        if not self.bus.read_reg(base + 3) & FULL_OFF:
            self.disable_all()
            raise RuntimeError("FULL OFF no se conserva tras programar el canal")
        return count


def print_snapshot(snapshot):
    print("=== PCA9685 /dev/i2c-1 / 0x40 ===")
    print("MODE1: 0x{:02x}".format(snapshot["mode1"]))
    print("MODE2: 0x{:02x}".format(snapshot["mode2"]))
    print("PRE_SCALE: 0x{:02x}".format(snapshot["pre_scale"]))
    print("Canales FULL OFF: {}/16".format(len(snapshot["off_channels"])))
    print("TODOS DESHABILITADOS: {}".format(
        "SI" if snapshot["all_off"] else "NO - NO ENERGIZAR SERVOS"
    ))
    print("OE: NO verificable por I2C; mantener OE -> 3.3 V")
    print("IMPORTANTE: FULL OFF no reemplaza un corte fisico de potencia")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Diagnostico seguro del PCA9685 Jetson sin habilitar servos"
    )
    parser.add_argument(
        "action", nargs="?", choices=("status", "disable-all"),
        default="status", help="status no escribe registros; disable-all solo apaga"
    )
    args = parser.parse_args(argv)
    try:
        controller = SafePCA9685(I2CToolsBus())
        if args.action == "disable-all":
            controller.disable_all()
            print("FULL OFF aplicado y comprobado en los 16 canales")
        snapshot = controller.inspect()
        print_snapshot(snapshot)
        return 0 if snapshot["all_off"] else 2
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print("ERROR I2C: {}".format(exc), file=sys.stderr)
        print("Mantener desconectada la fuente de servos y OE en 3.3 V", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
