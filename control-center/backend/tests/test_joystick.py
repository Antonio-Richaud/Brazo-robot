import unittest

from joystick_manager import normalize_axis


class NormalizeAxisTests(unittest.TestCase):
    def test_deadzone_returns_zero(self):
        self.assertEqual(normalize_axis(0.04, 0.0, deadzone=0.08), 0.0)

    def test_axis_is_normalized_around_calibrated_center(self):
        self.assertAlmostEqual(normalize_axis(1.0, 0.1), 1.0)
        self.assertAlmostEqual(normalize_axis(-1.0, 0.1), -1.0)

    def test_output_is_clamped(self):
        self.assertEqual(normalize_axis(4.0, 0.0), 1.0)


if __name__ == "__main__":
    unittest.main()
