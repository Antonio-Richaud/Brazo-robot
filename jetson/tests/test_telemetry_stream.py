"""Pruebas de telemetria JSONL aislada: Python 3.6, cero hardware."""

import contextlib
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arm_simulation import ArmSimulation  # noqa: E402
from telemetry_stream import (  # noqa: E402
    SCHEMA, SCHEMA_VERSION, SOURCE, main, make_frame, run_demo,
)


class FakeClock(object):
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class TelemetryStreamTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.output = io.StringIO()
        self.count = run_demo(
            clock=self.clock,
            sleep=self.clock.sleep,
            output=self.output,
        )
        self.lines = self.output.getvalue().splitlines()
        self.frames = [json.loads(line) for line in self.lines]

    def test_exactly_thirteen_independent_jsonl_frames(self):
        self.assertEqual(self.count, 13)
        self.assertEqual(len(self.frames), 13)
        self.assertEqual([frame["sequence"] for frame in self.frames],
                         list(range(13)))

    def test_contract_version_and_source(self):
        for frame in self.frames:
            self.assertEqual(frame["schema"], SCHEMA)
            self.assertEqual(frame["schema_version"], SCHEMA_VERSION)
            self.assertEqual(frame["source"], SOURCE)
            self.assertEqual(frame["mode"], "simulation_only")

    def test_never_hardware_enabled_or_measured(self):
        for frame in self.frames:
            self.assertIs(frame["hardware_enabled"], False)
            self.assertEqual(len(frame["servos"]), 6)
            self.assertTrue(all(
                servo["measured"] is False
                for servo in frame["servos"].values()
            ))

    def test_disarmed_at_start_and_end(self):
        self.assertEqual(self.frames[0]["state"], "DISARMED")
        self.assertEqual(self.frames[1]["state"], "SIM_ARMED")
        self.assertTrue(all(
            frame["state"] == "SIM_ARMED"
            for frame in self.frames[1:12]
        ))
        self.assertEqual(self.frames[12]["state"], "DISARMED")

    def test_base_moves_out_and_returns_without_overshoot(self):
        angles = [
            frame["servos"]["base"]["current"]
            for frame in self.frames
        ]
        self.assertEqual(angles, [
            90.0, 90.0, 97.0, 104.0, 111.0, 118.0, 125.0,
            118.0, 111.0, 104.0, 97.0, 90.0, 90.0
        ])
        self.assertEqual(self.frames[-1]["servos"]["base"]["target"], 90.0)

    def test_other_joint_angles_remain_home(self):
        expected = {
            "hombro": 50.0,
            "codo": 165.0,
            "muneca1": 10.0,
            "muneca2": 170.0,
            "garra": 40.0,
        }
        for frame in self.frames:
            for name, home in expected.items():
                self.assertEqual(frame["servos"][name]["current"], home)
                self.assertEqual(frame["servos"][name]["target"], home)

    def test_make_frame_rejects_invalid_sequence(self):
        sim = ArmSimulation(clock=self.clock)
        for invalid in (-1, True, 1.5, None, "0"):
            with self.assertRaises(ValueError):
                make_frame(sim, invalid)

    def test_frame_does_not_share_mutable_servo_state(self):
        sim = ArmSimulation(clock=self.clock)
        frame = make_frame(sim, 0)
        frame["servos"]["base"]["current"] = 999
        self.assertEqual(sim.snapshot()["servos"]["base"]["current"], 90.0)

    def test_cli_requires_explicit_demo_flag(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main([])
        self.assertEqual(caught.exception.code, 2)

    def test_output_is_only_jsonl_without_console_banners(self):
        self.assertEqual(self.output.getvalue().count("\n"), 13)
        self.assertNotIn("PWM", self.output.getvalue())
        self.assertNotIn("I2C", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
