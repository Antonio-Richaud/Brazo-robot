#!/usr/bin/env python3
"""Prueba MANUAL de la garra SG90 (PCA9685 ch5); NO es control autonomo.

Python 3.6 / Jetson Nano 2GB. Requiere SUPERVISION en persona:
- STOP real para cortar la fuente 5 V de servos, accesible en todo momento.
- OE DESCONECTADO del pin fijo J6-17 de 3.3 V y comprobado en LOW
  por pull-down de la propia placa PCA9685 (no dejar flotante sin medir).
- Los seis servos estan montados; no existe feedback ni calibracion real.
- NUNCA usar Home, Saludo o Rutina como primer movimiento.

Comandos:
  python3 jetson/garra_pulso_laboratorio.py preflight
  python3 jetson/garra_pulso_laboratorio.py pulse --confirm-oe-low --confirm-stop-ready

'preflight' nunca habilita PWM. 'pulse' habilita SOLO canal 5 durante
250 ms (1500 us) y luego ejecuta FULL OFF 16/16 en un finally.
Ante un bloqueo de Linux o bus I2C, FULL OFF NO esta garantizado: usar STOP.
"""

import argparse
import sys
import time

from pca9685_safe import (
    EXPECTED_PRE_SCALE,
    FULL_OFF,
    MODE1,
    MODE2,
    PRE_SCALE,
    SafePCA9685,
    I2CToolsBus,
    channel_off_high_register,
)


GARRA_CHANNEL = 5
GARRA_PULSE_US = 1500
PULSE_DURATION_S = 0.25
EXPECTED_MODE1 = 0x01
EXPECTED_MODE2 = 0x04


class GarraLaboratorio(object):
    """Unico servo, un solo pulso, operaciones de I2C sin cambiar GPIO/OE."""

    def __init__(self, bus, sleeper=None):
        self.bus = bus
        self.sleeper = sleeper or time.sleep
        self.controller = SafePCA9685(bus)

    def preflight(self):
        # La primera escritura siempre bloquea TODAS las salidas.
        self.controller.disable_all()
        snapshot = self.controller.inspect()

        if snapshot["mode2"] != EXPECTED_MODE2:
            raise RuntimeError("MODE2 no esperado; conservar STOP")

        if snapshot["mode1"] != EXPECTED_MODE1 or (
                snapshot["pre_scale"] != EXPECTED_PRE_SCALE):
            # Segun NXP: PRE_SCALE solo puede modificarse estando SLEEP=1.
            # FULL OFF sigue activo durante toda esta secuencia.
            self.bus.write_reg(MODE1, 0x11)
            self.bus.write_reg(PRE_SCALE, EXPECTED_PRE_SCALE)
            self.bus.write_reg(MODE1, EXPECTED_MODE1)
            self.sleeper(0.02)

        snapshot = self.controller.inspect()
        if (snapshot["mode1"] != EXPECTED_MODE1 or
                snapshot["mode2"] != EXPECTED_MODE2 or
                snapshot["pre_scale"] != EXPECTED_PRE_SCALE or
                not snapshot["all_off"]):
            raise RuntimeError("Configuracion PCA9685 invalida; conservar STOP")

        count = self.controller.stage_disabled_pulse(
            GARRA_CHANNEL, GARRA_PULSE_US)
        if count != 307 or not self.controller.all_channels_off():
            raise RuntimeError("Garra no preparada correctamente; conservar STOP")
        register = channel_off_high_register(GARRA_CHANNEL)
        if self.bus.read_reg(register) != (FULL_OFF | ((count >> 8) & 0x0F)):
            raise RuntimeError("Registro garra no coincide; conservar STOP")
        return count

    def pulse(self):
        """Pulso breve, NO repetitivo. Operador debe tener STOP a mano."""
        count = self.preflight()
        register = channel_off_high_register(GARRA_CHANNEL)
        enabled_value = ((count >> 8) & 0x0F)  # Quitar SOLO FULL OFF canal 5
        try:
            self.bus.write_reg(register, enabled_value)
            # La lectura se omite durante el pulso para acotar su duracion.
            self.sleeper(PULSE_DURATION_S)
        finally:
            # En un cierre normal o KeyboardInterrupt, devolver FULL OFF 16/16.
            # No puede recuperar un freeze de OS, bus I2C o perdida de energia.
            self.controller.disable_all()

        if not self.controller.all_channels_off():
            raise RuntimeError("NO se pudo verificar FULL OFF; ACTIVAR STOP")
        return count


def main(argv=None, bus=None, sleeper=None):
    parser = argparse.ArgumentParser(
        description="Prueba de garra: preflight enmascarado o pulso fisico 250 ms"
    )
    parser.add_argument("action", choices=("preflight", "pulse"))
    parser.add_argument("--confirm-oe-low", action="store_true",
                        help="He medido OE ~0 V tras desconectar J6 pin17")
    parser.add_argument("--confirm-stop-ready", action="store_true",
                        help="Estoy presente, brazo despejado, STOP a mano")
    args = parser.parse_args(argv)

    if args.action == "pulse" and not (
            args.confirm_oe_low and args.confirm_stop_ready):
        parser.error(
            "pulse exige --confirm-oe-low y --confirm-stop-ready; "
            "NO ejecutar a ciegas"
        )

    try:
        lab = GarraLaboratorio(
            bus if bus is not None else I2CToolsBus(), sleeper=sleeper)
        if args.action == "preflight":
            count = lab.preflight()
            print("PREFLIGHT_OK: garra canal 5; {} cuentas".format(count))
            print("FULL OFF 16/16; sin PWM fisico")
        else:
            count = lab.pulse()
            print("PULSE_FINISHED: garra canal 5, {} us, 250 ms".format(
                GARRA_PULSE_US))
            print("FULL OFF 16/16 comprobado")
            print("IMPORTANTE: ACTIVAR STOP si hubo movimiento anormal")
        return 0
    except (OSError, RuntimeError, ValueError, KeyboardInterrupt) as exc:
        print("ERROR O INTERRUPCION: {}".format(exc), file=sys.stderr)
        print("ACTIVAR STOP FISICO AHORA. No confiar en cierre de software",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
