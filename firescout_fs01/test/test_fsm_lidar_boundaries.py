"""LiDAR classification -> real FSM -> command boundary regressions, no ramp needed."""

import ast
from pathlib import Path
import unittest

import test_fsm_node as harness


# Exercise the real LiDAR classifier without importing ROS into this test.
source = Path(__file__).parents[1] / 'scripts/lidar_monitor.py'
function = next(n for n in ast.parse(source.read_text()).body
                if isinstance(n, ast.FunctionDef) and n.name == 'obstacle_status')
namespace = {}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
classify = namespace['obstacle_status']


class LidarFsmBoundaryTests(unittest.TestCase):
    def setUp(self):
        previous_time = harness.FSM_MODULE.time
        self.addCleanup(setattr, harness.FSM_MODULE, 'time', previous_time)

    def run_case(self, distance, camera='SEARCHING', imu='NORMAL', enabled=True):
        case = harness.TestFSMNode()
        case.setUp()
        status = classify(distance, 0.70, 1.20)
        case.prime(lidar=status, front=distance, camera=camera, imu=imu)
        case.node.on_open_side(harness.FakeMessage('LEFT'))
        case.node.on_left_distance(harness.FakeMessage(2.0))
        if enabled:
            case.enable()
        command = case.tick()
        return case, status, command

    def test_clear_at_old_stop_point_uses_caution(self):
        case, status, command = self.run_case(1.498)
        self.assertEqual(status, 'CLEAR')
        self.assertEqual(case.status(), 'CAUTION')
        self.assertEqual(command, (0.02, 0.0))

    def test_classification_state_and_command_boundaries(self):
        cases = [
            (1.5001, 'CLEAR', 'EXPLORE', (0.04, 0.0)),
            (1.5000, 'CLEAR', 'CAUTION', (0.02, 0.0)),
            (1.4999, 'CLEAR', 'CAUTION', (0.02, 0.0)),
            (1.2001, 'CLEAR', 'CAUTION', (0.02, 0.0)),
            (1.2000, 'CLEAR', 'CAUTION', (0.02, 0.0)),
            (1.1999, 'WARNING', 'CAUTION', (0.02, 0.0)),
            (0.8001, 'WARNING', 'CAUTION', (0.02, 0.0)),
            (0.8000, 'WARNING', 'CAUTION', (0.0, 0.0)),
            (0.7999, 'WARNING', 'CAUTION', (0.0, 0.0)),
            (0.7001, 'WARNING', 'CAUTION', (0.0, 0.0)),
            (0.7000, 'WARNING', 'CAUTION', (0.0, 0.0)),
            (0.6999, 'DANGER', 'AVOID', (0.0, 0.25)),
        ]
        for distance, lidar, state, command in cases:
            with self.subTest(distance=distance):
                case, actual_lidar, actual_command = self.run_case(distance)
                self.assertEqual(actual_lidar, lidar)
                self.assertEqual(case.status(), state)
                self.assertEqual(actual_command, command)

    def test_caution_band_keeps_camera_tilt_and_motion_guards(self):
        for distance in (1.5, 1.498, 1.2, 0.95):
            for camera, imu, enabled in (
                    ('STALE', 'NORMAL', True), ('SEARCHING', 'WARNING', True),
                    ('SEARCHING', 'UNKNOWN', True), ('SEARCHING', 'NORMAL', False)):
                with self.subTest(distance=distance, camera=camera, imu=imu, enabled=enabled):
                    case, _, command = self.run_case(distance, camera, imu, enabled)
                    self.assertEqual(command, (0.0, 0.0))
                    if camera == 'STALE' or imu != 'NORMAL':
                        self.assertEqual(case.status(), 'SAFE_STOP')

    def test_caution_band_stale_front_still_stops(self):
        case, _, _ = self.run_case(1.498)
        case.now += 1.1
        case.node.on_lidar(harness.FakeMessage('CLEAR'))
        case.node.on_camera_status(harness.FakeMessage('SEARCHING'))
        case.node.on_imu(harness.FakeMessage('NORMAL'))
        self.assertEqual(case.tick(), (0.0, 0.0))
        self.assertEqual(case.status(), 'SAFE_STOP')


if __name__ == '__main__':
    unittest.main()
