"""Pruebas del monitor replay Jetson SIN abrir puertos ni mover hardware."""

import contextlib
import io
import json
import os
import sys
import unittest
from unittest.mock import patch

from jetson_demo_monitor import (
    MONITOR_HOST,
    MONITOR_PORT,
    RUNTIME_LABEL,
    apply_frame,
    create_monitor_state,
    create_monitor_websocket,
    main,
    replay_frames,
)
from jetson_telemetry_reader import read_demo_stream

JETSON_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "jetson")
)
sys.path.insert(0, JETSON_DIR)
from telemetry_stream import run_demo  # noqa: E402


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class JetsonDemoMonitorTests(unittest.TestCase):
    def setUp(self):
        clock = FakeClock()
        stream = io.StringIO()
        run_demo(clock=clock, sleep=clock.sleep, output=stream)
        self.frames = read_demo_stream(stream.getvalue().splitlines())
        self.state = create_monitor_state()

    def test_initial_mode_is_monitor_not_hardware(self):
        snapshot = self.state.snapshot()
        self.assertEqual(snapshot["runtime_mode"], RUNTIME_LABEL)
        self.assertEqual(snapshot["mode"], "monitor")
        self.assertIs(snapshot["connected"], False)
        self.assertIsNone(snapshot["port"])
        self.assertIs(snapshot["joystick_connected"], False)

    def test_monitor_websocket_is_local_and_has_no_command_handler(self):
        ws = create_monitor_websocket(self.state)
        self.assertEqual(ws.host, "127.0.0.1")
        self.assertEqual(ws.host, MONITOR_HOST)
        self.assertEqual(ws.port, 8767)
        self.assertEqual(ws.port, MONITOR_PORT)
        self.assertIsNone(ws.command_handler)
        # La prueba no llama ws.start(): jamas abre sockets.

    def test_replay_follows_all_thirteen_frames(self):
        observed = []
        replay_frames(
            self.state,
            self.frames,
            sleep=lambda _: observed.append(
                self.state.snapshot()["servos"]["base"]["current"]
            ),
        )
        self.assertEqual(observed, [
            90.0, 90.0, 97.0, 104.0, 111.0, 118.0, 125.0,
            118.0, 111.0, 104.0, 97.0, 90.0, 90.0,
        ])
        self.assertEqual(self.state.snapshot()["servos"]["base"]["target"], 90.0)

    def test_replay_does_not_set_last_command_timestamp(self):
        replay_frames(self.state, self.frames, sleep=lambda _: None)
        self.assertIsNone(
            self.state.snapshot()["health"]["last_command_at"]
        )
        self.assertEqual(self.state.get_mode(), "monitor")

    def test_other_five_joints_remain_at_home(self):
        replay_frames(self.state, self.frames, sleep=lambda _: None)
        actual = self.state.snapshot()["servos"]
        homes = {
            "hombro": 50.0, "codo": 165.0, "muneca1": 10.0,
            "muneca2": 170.0, "garra": 40.0,
        }
        for name, home in homes.items():
            self.assertEqual(actual[name]["current"], home)
            self.assertEqual(actual[name]["target"], home)
            self.assertIs(actual[name]["measured"], False)

    def test_wrong_runtime_is_rejected(self):
        self.state.set_runtime_mode("hardware")
        with self.assertRaises(RuntimeError):
            apply_frame(self.state, self.frames[0])

    def test_wrong_mode_is_rejected(self):
        self.state.set_mode("manual")
        with self.assertRaises(RuntimeError):
            apply_frame(self.state, self.frames[0])

    def test_cli_requires_explicit_stdin_demo(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main([])
        self.assertEqual(caught.exception.code, 2)

    def test_bad_stream_fails_before_websocket_creation(self):
        with patch(
            "jetson_demo_monitor.sys.stdin", io.StringIO('not json\n')
        ), patch(
            "jetson_demo_monitor.create_monitor_websocket"
        ) as mocked_ws, contextlib.redirect_stderr(io.StringIO()):
            result = main(["--stdin-demo"])
        self.assertEqual(result, 1)
        mocked_ws.assert_not_called()

    def test_no_mutation_of_input_frames(self):
        original = json.dumps(self.frames, sort_keys=True)
        replay_frames(self.state, self.frames, sleep=lambda _: None)
        self.assertEqual(json.dumps(self.frames, sort_keys=True), original)


if __name__ == "__main__":
    unittest.main()
