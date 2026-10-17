import unittest

from config import HOME
from controller import RobotController
from raspberry_pi_driver import RaspberryPiMotionDriver, smootherstep
from robot_state import RobotState


class FakeChannel:
    def __init__(self):
        self.duty_cycle = 0


class FakePCA:
    def __init__(self):
        self.channels = [FakeChannel() for _ in range(16)]
        self.frequency = None
        self.closed = False

    def deinit(self):
        self.closed = True


class RaspberryPiDriverTests(unittest.TestCase):
    def setUp(self):
        self.state = RobotState()
        self.pca = FakePCA()
        self.events = []
        self.driver = RaspberryPiMotionDriver(
            self.state,
            pca_factory=lambda: self.pca,
            event_handler=self.events.append,
        )

    def test_no_pwm_until_explicit_arm(self):
        self.driver.connect()
        self.assertTrue(self.driver.connected)
        self.assertFalse(self.driver.armed)
        self.assertFalse(self.state.snapshot()["armed"])
        self.assertEqual(self.pca.frequency, 50)
        self.assertTrue(all(channel.duty_cycle == 0 for channel in self.pca.channels))
        self.assertFalse(self.driver.send("s 1 120"))
        self.driver.tick()
        self.assertTrue(all(channel.duty_cycle == 0 for channel in self.pca.channels))
        self.assertTrue(self.driver.arm())
        self.assertTrue(all(self.pca.channels[index].duty_cycle > 0 for index in range(6)))
        self.assertTrue(self.state.snapshot()["armed"])

    def test_manual_motion_limits_and_smoothing(self):
        self.driver.connect()
        self.driver.arm()
        self.assertTrue(self.driver.send("s 1 999"))
        self.assertEqual(self.driver.axes[1].target, 170)
        self.assertTrue(self.driver.send("s 6 -999"))
        self.assertEqual(self.driver.axes[6].target, 20)
        before = self.driver.axes[1].current
        self.driver.tick(self.driver._last_motion_at + 0.03)
        self.assertGreater(self.driver.axes[1].current, before)
        self.assertLess(self.driver.axes[1].current, 170)
        self.assertLessEqual(self.driver.axes[1].velocity, 260 * 0.03 + 1e-6)

    def test_sequence_ends_in_home_and_resumes_manual(self):
        self.driver.connect()
        self.driver.arm()
        self.assertTrue(self.driver.send("saludo"))
        self.assertFalse(self.driver.send("s 1 130"))
        self.assertIn("saludo_started", self.events)
        sequence = self.driver._sequence
        for duration, hold, _ in sequence["steps"]:
            next_time = sequence["started"] + duration + hold + 0.01
            self.driver.tick(next_time)
        self.assertIsNone(self.driver._sequence)
        self.assertIn("saludo_finished", self.events)
        self.assertTrue(self.driver.send("s 1 120"))
        self.assertEqual(self.driver.axes[1].target, 120)

    def test_stop_moves_toward_home_not_emergency_off(self):
        self.driver.connect()
        self.driver.arm()
        self.driver.send("rutina")
        self.assertTrue(self.driver.send("stop"))
        self.assertIsNone(self.driver._sequence)
        self.assertEqual(
            {key: axis.target for key, axis in self.driver.axes.items()},
            {key: float(val) for key, val in HOME.items()},
        )
        self.assertTrue(self.driver.armed)
        self.assertIn("choreo_stopped", self.events)

    def test_disarm_releases_pwm(self):
        self.driver.connect()
        self.driver.arm()
        self.assertTrue(self.driver.disarm())
        self.assertFalse(self.driver.armed)
        self.assertFalse(self.state.snapshot()["armed"])
        self.assertTrue(all(channel.duty_cycle == 0 for channel in self.pca.channels))
        self.assertFalse(self.driver.send("home"))
        self.driver.disconnect()
        self.assertTrue(self.pca.closed)
        self.assertFalse(self.driver.connected)

    def test_rejects_bad_commands_and_ranges(self):
        self.driver.connect()
        self.driver.arm()
        for command in ("s 9 40", "s 1 nan", "range 2 180 10", "range 2 -1 180", "unknown", "d 1 inf"):
            self.assertFalse(self.driver.send(command))
        self.assertTrue(self.driver.send("d 1 10"))
        self.assertEqual(self.driver.axes[1].target, 100)

    def test_controller_arm_and_disarm(self):
        self.driver.connect()
        controller = RobotController(self.state, self.driver)
        self.assertFalse(controller.handle_command(
            {"action": "set_servo", "servo_id": 1, "angle": 120}
        ))
        self.assertTrue(controller.handle_command({"action": "arm"}))
        self.assertTrue(controller.handle_command(
            {"action": "set_servo", "servo_id": 1, "angle": 120}
        ))
        self.assertTrue(controller.handle_command({"action": "disarm"}))
        self.assertFalse(controller.handle_command({"action": "saludo"}))

    def test_smootherstep_and_telemetry(self):
        self.assertAlmostEqual(smootherstep(0.5), 0.5)
        self.assertEqual(smootherstep(-10), 0)
        self.assertEqual(smootherstep(10), 1)
        self.driver.connect()
        self.driver.arm()
        status = self.state.snapshot()
        self.assertEqual(status["port"], "I2C-1 / 0x40")
        self.assertEqual(status["servos"]["base"]["pca_channel"], 0)
        self.assertFalse(status["servos"]["base"]["measured"])


if __name__ == "__main__":
    unittest.main()
