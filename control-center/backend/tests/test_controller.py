import unittest

from controller import RobotController
from robot_state import RobotState


class FakeSerial:
    def __init__(self):
        self.connected = True
        self.commands = []

    def send(self, command):
        self.commands.append(command)
        return True


class FakeJoystick:
    def __init__(self):
        self.manual_enabled = True
        self.targets = {}
        self.last_sent = {}

    def set_manual_enabled(self, enabled):
        self.manual_enabled = enabled


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.state = RobotState()
        self.serial = FakeSerial()
        self.controller = RobotController(self.state, self.serial)
        self.joystick = FakeJoystick()
        self.controller.attach_joystick(self.joystick)

    def test_choreography_completion_restores_manual_control(self):
        self.assertTrue(self.controller.handle_command({"action": "saludo"}))
        self.assertFalse(self.controller.manual_enabled)
        self.assertFalse(self.joystick.manual_enabled)

        self.controller.handle_protocol_event("saludo_finished")

        self.assertTrue(self.controller.manual_enabled)
        self.assertTrue(self.joystick.manual_enabled)
        self.assertEqual(self.state.snapshot()["mode"], "manual")

    def test_set_servo_marks_only_changed_servo_dirty(self):
        self.controller.last_sent = {servo_id: 90 for servo_id in range(1, 7)}
        self.assertTrue(
            self.controller.handle_command(
                {"action": "set_servo", "servo_id": 2, "angle": 80}
            )
        )
        dirty = [key for key, value in self.controller.last_sent.items() if value is None]
        self.assertEqual(dirty, [2])

    def test_rejects_motion_during_choreography(self):
        self.controller.handle_command({"action": "rutina"})
        self.assertFalse(
            self.controller.handle_command(
                {"action": "set_servo", "servo_id": 1, "angle": 120}
            )
        )

    def test_clamps_servo_angle(self):
        self.controller.handle_command(
            {"action": "set_servo", "servo_id": 6, "angle": 999}
        )
        self.assertEqual(self.controller.targets[6], 140)


if __name__ == "__main__":
    unittest.main()
