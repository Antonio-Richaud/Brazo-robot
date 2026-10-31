"""Pruebas del receptor Mac sin hardware, red, motores ni SSH real."""

import io
import json
import os
import sys
import unittest

from jetson_telemetry_reader import (
    TelemetryValidationError,
    read_demo_stream,
    validate_frame,
)

JETSON_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "jetson")
)
sys.path.insert(0, JETSON_DIR)
from telemetry_stream import run_demo  # noqa: E402


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class JetsonTelemetryReaderTests(unittest.TestCase):
    def setUp(self):
        fake_clock = FakeClock()
        output = io.StringIO()
        count = run_demo(
            clock=fake_clock, sleep=fake_clock.sleep, output=output
        )
        self.assertEqual(count, 13)
        self.lines = output.getvalue().splitlines(keepends=True)

    def changed(self, index, mutate):
        lines = list(self.lines)
        frame = json.loads(lines[index])
        mutate(frame)
        lines[index] = json.dumps(frame) + "\n"
        return lines

    def test_accept_real_python36_emitter_contract(self):
        frames = read_demo_stream(self.lines)
        self.assertEqual(len(frames), 13)
        self.assertEqual(frames[0]["state"], "DISARMED")
        self.assertEqual(frames[-1]["state"], "DISARMED")
        self.assertEqual(frames[6]["servos"]["base"]["current"], 125.0)
        self.assertEqual(frames[12]["servos"]["base"]["current"], 90.0)

    def test_reject_hardware_enabled(self):
        lines = self.changed(5, lambda f: f.update(hardware_enabled=True))
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_measured_true(self):
        lines = self.changed(
            4, lambda f: f["servos"]["base"].update(measured=True)
        )
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_bad_schema(self):
        lines = self.changed(0, lambda f: f.update(schema="unknown"))
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_wrong_version(self):
        lines = self.changed(0, lambda f: f.update(schema_version=2))
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_unknown_source(self):
        lines = self.changed(0, lambda f: f.update(source="hardware"))
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_mode_that_is_not_simulation_only(self):
        lines = self.changed(2, lambda f: f.update(mode="hardware"))
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_nonsequential_number(self):
        lines = self.changed(3, lambda f: f.update(sequence=999))
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_boolean_sequence(self):
        lines = self.changed(2, lambda f: f.update(sequence=True))
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_changed_joint_map(self):
        lines = self.changed(
            4,
            lambda f: f["servos"].update(
                {"unknown_joint": f["servos"].pop("base")}
            ),
        )
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_wrong_pca_channel(self):
        lines = self.changed(
            3, lambda f: f["servos"]["base"].update(pca_channel=15)
        )
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_angle_out_of_limits(self):
        lines = self.changed(
            2, lambda f: f["servos"]["base"].update(current=999)
        )
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_angle_nan(self):
        lines = self.changed(
            4, lambda f: f["servos"]["base"].update(current=float("nan"))
        )
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_missing_frame(self):
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(self.lines[:-1])

    def test_reject_extra_frame(self):
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(self.lines + self.lines[-1:])

    def test_reject_garbage_or_empty_line(self):
        for extra in ('not json\n', '\n'):
            lines = list(self.lines)
            lines[4] = extra
            with self.assertRaises(TelemetryValidationError):
                read_demo_stream(lines)

    def test_reject_oversized_line(self):
        lines = list(self.lines)
        lines[5] = " " * 16385
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_initially_armed(self):
        lines = self.changed(0, lambda f: f.update(state="SIM_ARMED"))
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_fault_state_in_demo(self):
        lines = self.changed(
            6, lambda f: f.update(state="FAULT", fault_reason="timeout")
        )
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_unexpected_motion_trajectory(self):
        lines = self.changed(
            5, lambda f: f["servos"]["base"].update(current=116)
        )
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_no_return_to_home(self):
        lines = self.changed(
            12, lambda f: f["servos"]["base"].update(current=120)
        )
        with self.assertRaises(TelemetryValidationError):
            read_demo_stream(lines)

    def test_reject_malformed_structure(self):
        for frame in ("[]", "null", '"text"'):
            with self.assertRaises(TelemetryValidationError):
                validate_frame(json.loads(frame), 0)


if __name__ == "__main__":
    unittest.main()
