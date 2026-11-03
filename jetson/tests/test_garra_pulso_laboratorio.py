"""Tests sin hardware de una prueba manual de garra SG90, Python 3.6."""

import io
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from garra_pulso_laboratorio import (  # noqa: E402
    GARRA_CHANNEL,
    PULSE_DURATION_S,
    GarraLaboratorio,
    main,
)
from pca9685_safe import (  # noqa: E402
    ALL_LED_OFF_H,
    EXPECTED_PRE_SCALE,
    FULL_OFF,
    MODE1,
    MODE2,
    PRE_SCALE,
    channel_off_high_register,
)


class FakeBus(object):
    def __init__(self, blocked_write=None, ignore_disable=False):
        self.regs = {MODE1: 0x01, MODE2: 0x04, PRE_SCALE: EXPECTED_PRE_SCALE}
        for channel in range(16):
            self.regs[channel_off_high_register(channel)] = FULL_OFF
        self.writes = []
        self.blocked_write = blocked_write
        self.ignore_disable = ignore_disable

    def read_reg(self, register):
        return self.regs.get(register, 0)

    def write_reg(self, register, value):
        self.writes.append((register, value))
        if self.blocked_write == (register, value):
            raise OSError("i2cset failed")
        if register == ALL_LED_OFF_H:
            if not self.ignore_disable:
                for channel in range(16):
                    self.regs[channel_off_high_register(channel)] = value
        else:
            self.regs[register] = value


class GarraLaboratorioTests(unittest.TestCase):
    def setUp(self):
        self.bus = FakeBus()
        self.sleep_calls = []
        self.lab = GarraLaboratorio(
            self.bus, sleeper=self.sleep_calls.append)

    def test_preflight_never_enables_output(self):
        self.assertEqual(self.lab.preflight(), 307)
        self.assertEqual(self.bus.regs[channel_off_high_register(5)], 0x11)
        self.assertTrue(self.lab.controller.all_channels_off())
        for r, v in self.bus.writes:
            if r == channel_off_high_register(5):
                self.assertTrue(v & FULL_OFF)
        self.assertEqual(self.sleep_calls, [])

    def test_preflight_can_restore_frequency_while_all_off(self):
        self.bus.regs[MODE1] = 0x11
        self.bus.regs[PRE_SCALE] = 0x1e
        self.assertEqual(self.lab.preflight(), 307)
        self.assertEqual(self.bus.regs[MODE1], 0x01)
        self.assertEqual(self.bus.regs[PRE_SCALE], 0x79)
        self.assertIn((MODE1, 0x11), self.bus.writes)
        self.assertIn((PRE_SCALE, 0x79), self.bus.writes)
        self.assertIn((MODE1, 0x01), self.bus.writes)
        self.assertTrue(self.lab.controller.all_channels_off())

    def test_pulse_only_enables_garra_and_then_disables_all(self):
        observed_states = []
        def sleeper(seconds):
            observed_states.append((seconds, [self.bus.regs[
                channel_off_high_register(n)] for n in range(16)]))
        lab = GarraLaboratorio(self.bus, sleeper=sleeper)
        lab.pulse()
        self.assertEqual(len(observed_states), 1)
        duration, states = observed_states[0]
        self.assertEqual(duration, PULSE_DURATION_S)
        self.assertEqual(states[GARRA_CHANNEL], 0x01)
        self.assertTrue(all(state & FULL_OFF
                            for i, state in enumerate(states)
                            if i != GARRA_CHANNEL))
        self.assertTrue(lab.controller.all_channels_off())
        self.assertEqual(self.bus.writes[-1], (ALL_LED_OFF_H, FULL_OFF))

    def test_keyboard_interrupt_disables_all_in_finally(self):
        def interrupt(_seconds):
            raise KeyboardInterrupt("operator interruption")
        lab = GarraLaboratorio(self.bus, sleeper=interrupt)
        with self.assertRaises(KeyboardInterrupt):
            lab.pulse()
        self.assertTrue(lab.controller.all_channels_off())

    def test_write_failure_still_attempts_disable_all(self):
        self.bus.blocked_write = (channel_off_high_register(5), 0x01)
        with self.assertRaises(OSError):
            self.lab.pulse()
        self.assertTrue(self.lab.controller.all_channels_off())
        self.assertEqual(self.bus.writes[-1], (ALL_LED_OFF_H, FULL_OFF))

    def test_no_pulse_if_disable_all_not_accepted(self):
        self.bus.ignore_disable = True
        self.bus.regs[channel_off_high_register(2)] = 0x00
        with self.assertRaises(RuntimeError):
            self.lab.pulse()
        self.assertNotIn(
            (channel_off_high_register(5), 0x01), self.bus.writes)

    def test_no_pulse_if_mode2_unexpected(self):
        self.bus.regs[MODE2] = 0x05
        with self.assertRaises(RuntimeError):
            self.lab.pulse()
        self.assertNotIn(
            (channel_off_high_register(5), 0x01), self.bus.writes)

    def test_cli_rejects_pulse_without_both_confirmations_no_writes(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                main(["pulse", "--confirm-oe-low"], bus=self.bus,
                     sleeper=self.sleep_calls.append)
        self.assertEqual(exc.exception.code, 2)
        self.assertEqual(self.bus.writes, [])

    def test_cli_preflight_is_only_staging(self):
        out = io.StringIO()
        with redirect_stdout(out):
            result = main(["preflight"], bus=self.bus,
                          sleeper=self.sleep_calls.append)
        self.assertEqual(result, 0)
        self.assertIn("PREFLIGHT_OK", out.getvalue())
        self.assertTrue(self.lab.controller.all_channels_off())

    def test_cli_pulse_requires_and_accepts_both_confirmations(self):
        out = io.StringIO()
        with redirect_stdout(out):
            result = main(["pulse", "--confirm-oe-low",
                           "--confirm-stop-ready"], bus=self.bus,
                          sleeper=self.sleep_calls.append)
        self.assertEqual(result, 0)
        self.assertIn("PULSE_FINISHED", out.getvalue())
        self.assertEqual(self.sleep_calls, [PULSE_DURATION_S])
        self.assertTrue(self.lab.controller.all_channels_off())


if __name__ == "__main__":
    unittest.main()
