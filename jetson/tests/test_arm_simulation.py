"""Pruebas de simulacion pura para Python 3.6 sin acceso a hardware."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arm_simulation import (  # noqa: E402
    ArmSimulation,
    DISARMED,
    FAULT,
    JOINTS,
    SIM_ARMED,
)


class FakeClock(object):
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class ArmSimulationTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.arm = ArmSimulation(clock=self.clock)

    def test_default_disarmed_and_no_hardware(self):
        state = self.arm.snapshot()
        self.assertEqual(state["state"], DISARMED)
        self.assertFalse(state["hardware_enabled"])
        self.assertEqual(state["mode"], "simulation_only")
        self.assertEqual(len(state["servos"]), 6)
        for spec in JOINTS:
            servo = state["servos"][spec.name]
            self.assertEqual(servo["current"], spec.home)
            self.assertEqual(servo["target"], spec.home)
            self.assertEqual(servo["pca_channel"], spec.pca_channel)
            self.assertFalse(servo["measured"])

    def test_reject_command_when_disarmed(self):
        with self.assertRaises(RuntimeError):
            self.arm.set_target(1, 120)
        self.assertEqual(self.arm.snapshot()["servos"]["base"]["target"], 90)

    def test_simulated_arm_and_velocity_limit(self):
        self.arm.arm_simulation()
        self.assertEqual(self.arm.state, SIM_ARMED)
        self.arm.set_target(1, 150)
        self.clock.advance(0.1)
        self.arm.tick()
        self.assertAlmostEqual(self.arm.snapshot()["servos"]["base"]["current"], 97.0)
        self.clock.advance(0.1)
        self.arm.tick()
        self.assertAlmostEqual(self.arm.snapshot()["servos"]["base"]["current"], 104.0)

    def test_six_joint_limits(self):
        self.arm.arm_simulation()
        for spec in JOINTS:
            self.arm.set_target(spec.servo_id, spec.min_angle)
            self.arm.set_target(spec.servo_id, spec.max_angle)
            with self.assertRaises(ValueError):
                self.arm.set_target(spec.servo_id, spec.min_angle - 1)
            with self.assertRaises(ValueError):
                self.arm.set_target(spec.servo_id, spec.max_angle + 1)

    def test_invalid_servo_ids(self):
        self.arm.arm_simulation()
        for servo_id in (0, 7, -1, True, 1.0, "1", None):
            with self.assertRaises(ValueError):
                self.arm.set_target(servo_id, 90)

    def test_invalid_angles(self):
        self.arm.arm_simulation()
        for angle in (float("nan"), float("inf"), -float("inf"),
                      True, "90", None):
            with self.assertRaises(ValueError):
                self.arm.set_target(1, angle)
        self.assertEqual(self.arm.targets[1], 90.0)

    def test_watchdog_fault_stops_without_home_motion(self):
        self.arm.arm_simulation()
        self.arm.set_target(1, 160)
        self.clock.advance(1.01)
        state = self.arm.tick()
        self.assertEqual(state["state"], FAULT)
        self.assertEqual(state["servos"]["base"]["current"], 90)
        self.assertEqual(state["servos"]["base"]["target"], 90)
        self.assertIn("Watchdog", state["fault_reason"])

    def test_fault_requires_explicit_reset_and_rearm(self):
        self.arm.arm_simulation()
        self.clock.advance(1.1)
        self.arm.tick()
        with self.assertRaises(RuntimeError):
            self.arm.arm_simulation()
        with self.assertRaises(RuntimeError):
            self.arm.disarm_simulation()
        self.arm.reset_fault()
        self.assertEqual(self.arm.state, DISARMED)
        with self.assertRaises(RuntimeError):
            self.arm.set_target(1, 100)
        self.arm.arm_simulation()
        self.assertEqual(self.arm.state, SIM_ARMED)

    def test_heartbeat_refreshes_simulation_watchdog(self):
        self.arm.arm_simulation()
        self.arm.set_target(1, 170)
        for _ in range(5):
            self.clock.advance(0.5)
            self.arm.heartbeat()
            self.arm.tick()
        self.assertEqual(self.arm.state, SIM_ARMED)
        self.assertGreater(self.arm.positions[1], 90)

    def test_disarm_holds_simulated_position(self):
        self.arm.arm_simulation()
        self.arm.set_target(1, 160)
        self.clock.advance(0.1)
        self.arm.tick()
        moved = self.arm.positions[1]
        self.arm.disarm_simulation()
        self.clock.advance(10.0)
        self.arm.tick()
        self.assertEqual(self.arm.state, DISARMED)
        self.assertAlmostEqual(self.arm.positions[1], moved)
        self.assertAlmostEqual(self.arm.targets[1], moved)

    def test_no_jump_after_slow_tick(self):
        self.arm.arm_simulation()
        self.arm.set_target(1, 170)
        self.clock.advance(0.5)
        self.arm.tick()
        self.assertAlmostEqual(self.arm.positions[1], 97.0)

    def test_snapshot_is_defensive_copy(self):
        state = self.arm.snapshot()
        state["servos"]["base"]["target"] = -100
        self.assertEqual(self.arm.snapshot()["servos"]["base"]["target"], 90)

    def test_backward_clock_faults(self):
        self.arm.arm_simulation()
        self.clock.advance(-0.01)
        self.arm.tick()
        self.assertEqual(self.arm.state, FAULT)

    def test_rearm_and_fault_reset_invalid_transitions(self):
        self.arm.arm_simulation()
        with self.assertRaises(RuntimeError):
            self.arm.arm_simulation()
        with self.assertRaises(RuntimeError):
            self.arm.reset_fault()

    def test_invalid_watchdog_configuration(self):
        for value in (0, -1, float("nan"), float("inf"), True):
            with self.assertRaises(ValueError):
                ArmSimulation(clock=self.clock, watchdog_s=value)
            with self.assertRaises(ValueError):
                ArmSimulation(clock=self.clock, max_step_s=value)

    def test_invalid_command_does_not_extend_watchdog(self):
        self.arm.arm_simulation()
        self.clock.advance(0.9)
        with self.assertRaises(ValueError):
            self.arm.set_target(1, 999)
        self.clock.advance(0.11)
        self.arm.tick()
        self.assertEqual(self.arm.state, FAULT)

    def test_simulator_has_no_hardware_arming_interface(self):
        self.assertFalse(hasattr(self.arm, "set_pwm"))
        self.assertFalse(hasattr(self.arm, "write_reg"))
        self.assertFalse(hasattr(self.arm, "enable_output"))
        self.assertFalse(hasattr(self.arm, "set_servo_angle"))
        self.assertFalse(hasattr(self.arm, "bus"))


if __name__ == "__main__":
    unittest.main()
