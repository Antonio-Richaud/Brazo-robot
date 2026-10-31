"""Pruebas sin dispositivo fisico, compatibles con Python 3.6."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pca9685_safe import (  # noqa: E402
    ALL_LED_OFF_H,
    EXPECTED_PRE_SCALE,
    FULL_OFF,
    MODE1,
    MODE2,
    PRE_SCALE,
    SafePCA9685,
    I2CToolsBus,
    channel_off_high_register,
)


class FakeBus(object):
    def __init__(self, ignore_all_off=False):
        self.regs = {MODE1: 0x01, MODE2: 0x04, PRE_SCALE: EXPECTED_PRE_SCALE}
        for channel in range(16):
            self.regs[channel_off_high_register(channel)] = FULL_OFF
        self.writes = []
        self.ignore_all_off = ignore_all_off

    def read_reg(self, register):
        return self.regs.get(register, 0)

    def write_reg(self, register, value):
        self.writes.append((register, value))
        if register == ALL_LED_OFF_H:
            if not self.ignore_all_off:
                for channel in range(16):
                    self.regs[channel_off_high_register(channel)] = value
        else:
            self.regs[register] = value


class SafePCA9685Tests(unittest.TestCase):
    def setUp(self):
        self.bus = FakeBus()
        self.controller = SafePCA9685(self.bus)

    def test_status_is_read_only(self):
        state = self.controller.inspect()
        self.assertTrue(state["all_off"])
        self.assertEqual(state["pre_scale"], EXPECTED_PRE_SCALE)
        self.assertEqual(self.bus.writes, [])

    def test_disable_all_sets_full_off_on_each_channel(self):
        self.bus.regs[channel_off_high_register(4)] = 0
        self.assertFalse(self.controller.all_channels_off())
        self.controller.disable_all()
        self.assertTrue(self.controller.all_channels_off())
        self.assertEqual(self.bus.writes, [(ALL_LED_OFF_H, FULL_OFF)])

    def test_disable_all_fails_if_hardware_does_not_accept_command(self):
        self.bus.ignore_all_off = True
        self.bus.regs[channel_off_high_register(4)] = 0
        with self.assertRaises(RuntimeError):
            self.controller.disable_all()

    def test_stage_disabled_1500us_channel_zero(self):
        count = self.controller.stage_disabled_pulse(0, 1500)
        self.assertEqual(count, 307)
        self.assertEqual(self.bus.regs[0x08], 0x33)
        self.assertEqual(self.bus.regs[0x09], 0x11)
        self.assertTrue(self.controller.all_channels_off())

    def test_no_stage_if_any_channel_is_enabled(self):
        self.bus.regs[channel_off_high_register(1)] = 0
        with self.assertRaises(RuntimeError):
            self.controller.stage_disabled_pulse(0, 1500)
        self.assertEqual(self.bus.writes, [])

    def test_no_stage_with_wrong_prescale(self):
        self.bus.regs[PRE_SCALE] = 0x1E
        with self.assertRaises(RuntimeError):
            self.controller.stage_disabled_pulse(0, 1500)
        self.assertEqual(self.bus.writes, [])

    def test_no_stage_out_of_range(self):
        for channel, pulse_us in [(-1, 1500), (6, 1500), (0, 800), (0, 2500)]:
            with self.assertRaises(ValueError):
                self.controller.stage_disabled_pulse(channel, pulse_us)
        self.assertEqual(self.bus.writes, [])

    def test_transport_restricts_bus_and_address(self):
        with self.assertRaises(ValueError):
            I2CToolsBus(bus_number=0)
        with self.assertRaises(ValueError):
            I2CToolsBus(address=0x70)

    def test_no_enable_or_arm_api(self):
        self.assertFalse(hasattr(self.controller, "enable"))
        self.assertFalse(hasattr(self.controller, "arm"))
        self.assertFalse(hasattr(self.controller, "set_servo_angle"))


if __name__ == "__main__":
    unittest.main()
