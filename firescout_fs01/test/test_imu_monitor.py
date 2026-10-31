"""Freshness and orientation tests without starting ROS or a simulator."""

import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from rclpy.parameter import Parameter
from sensor_msgs.msg import Imu


spec = importlib.util.spec_from_file_location(
    'imu_monitor', Path(__file__).parents[1] / 'scripts' / 'imu_monitor.py'
)
imu_monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imu_monitor)


class OrientationTest(unittest.TestCase):
    def make_msg(self, components=(0.0, 0.0, 0.0, 1.0)):
        msg = Imu()
        msg.orientation.x, msg.orientation.y, msg.orientation.z, msg.orientation.w = components
        return msg

    def test_identity_with_unknown_and_known_uncertainty(self):
        msg = self.make_msg()
        angles, validity = imu_monitor.orientation_to_roll_pitch(msg)
        self.assertEqual(angles, (0.0, 0.0))
        self.assertIn('uncertainty unknown', validity)
        msg.orientation_covariance[0] = 0.01
        msg.orientation_covariance[4] = 0.01
        msg.orientation_covariance[8] = 0.01
        angles, validity = imu_monitor.orientation_to_roll_pitch(msg)
        self.assertEqual(angles, (0.0, 0.0))
        self.assertEqual(validity, 'VALID')

    def test_known_rotations_and_equivalent_negative_quaternion(self):
        # Mixed case: Rz(90) Ry(30) Rx(90); yaw must not be mistaken for roll.
        mixed = (math.sqrt(2) / 4, math.sqrt(6) / 4,
                 math.sqrt(2) / 4, math.sqrt(6) / 4)
        cases = [
            ((math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)), (90.0, 0.0)),
            ((-0.5, 0.0, 0.0, math.sqrt(3) / 2), (-60.0, 0.0)),
            ((0.0, 0.5, 0.0, math.sqrt(3) / 2), (0.0, 60.0)),
            ((0.0, -0.5, 0.0, math.sqrt(3) / 2), (0.0, -60.0)),
            ((0.0, 0.0, math.sqrt(0.5), math.sqrt(0.5)), (0.0, 0.0)),
            (mixed, (90.0, 30.0)),
        ]
        for components, expected in cases:
            for sign in (1, -1):
                with self.subTest(components=components, sign=sign):
                    angles, validity = imu_monitor.orientation_to_roll_pitch(
                        self.make_msg(tuple(sign * value for value in components))
                    )
                    self.assertTrue(validity.startswith('VALID'))
                    self.assertAlmostEqual(angles[0], expected[0], places=9)
                    self.assertAlmostEqual(angles[1], expected[1], places=9)

    def test_orientation_unavailable_even_with_identity(self):
        msg = self.make_msg()
        msg.orientation_covariance[0] = -1.0
        angles, validity = imu_monitor.orientation_to_roll_pitch(msg)
        self.assertIsNone(angles)
        self.assertTrue(validity.startswith('UNAVAILABLE'))

    def test_invalid_components_and_norms(self):
        cases = [(0.0,) * 4, (1e-13, 0.0, 0.0, 0.0),
                 (0.0, 0.0, 0.0, 1.0011), (0.0, 0.0, 0.0, 0.9989),
                 (1e308,) * 4]
        for invalid in (float('nan'), float('inf'), -float('inf')):
            for index in range(4):
                components = [0.0, 0.0, 0.0, 1.0]
                components[index] = invalid
                cases.append(tuple(components))
        for components in cases:
            with self.subTest(components=components):
                angles, validity = imu_monitor.orientation_to_roll_pitch(self.make_msg(components))
                self.assertIsNone(angles)
                self.assertTrue(validity.startswith('INVALID'))

    def test_small_norm_errors_are_normalized(self):
        for scale in (0.9991, 1.0009):
            msg = self.make_msg((0.0, 0.5 * scale, 0.0, math.sqrt(3) / 2 * scale))
            angles, _ = imu_monitor.orientation_to_roll_pitch(msg)
            self.assertAlmostEqual(angles[0], 0.0, places=9)
            self.assertAlmostEqual(angles[1], 60.0, places=9)

    def test_pitch_singularity_stays_finite(self):
        for sign in (1, -1):
            msg = self.make_msg((0.0, sign * math.sqrt(0.5), 0.0, math.sqrt(0.5)))
            angles, _ = imu_monitor.orientation_to_roll_pitch(msg)
            self.assertTrue(all(math.isfinite(value) for value in angles))
            self.assertAlmostEqual(angles[1], sign * 90.0, places=5)


class TiltHysteresisTest(unittest.TestCase):
    def test_boundaries_and_negative_angles(self):
        for previous in ('UNKNOWN', 'NORMAL', 'WARNING'):
            for sign in (-1, 1):
                for axis in (0, 1):
                    for value, expected in ((12.0, 'NORMAL'), (15.0, 'WARNING'), (20.0, 'WARNING')):
                        angles = [0.0, 0.0]
                        angles[axis] = sign * value
                        with self.subTest(previous=previous, angles=angles):
                            self.assertEqual(imu_monitor.next_tilt_status(previous, angles), expected)

    def test_deadband_remembers_state_and_unknown_is_conservative(self):
        for angles in ((14.0, 0.0), (0.0, -13.0), (-14.0, 13.0)):
            for previous, expected in (('NORMAL', 'NORMAL'), ('WARNING', 'WARNING'),
                                       ('UNKNOWN', 'WARNING')):
                self.assertEqual(imu_monitor.next_tilt_status(previous, angles), expected)
        for previous in ('NORMAL', 'WARNING', 'UNKNOWN'):
            self.assertEqual(imu_monitor.next_tilt_status(previous, None), 'UNKNOWN')

    def test_full_sequence(self):
        state = 'UNKNOWN'
        for value, expected in ((0, 'NORMAL'), (14, 'NORMAL'), (15, 'WARNING'),
                                (14, 'WARNING'), (12, 'NORMAL'), (-16, 'WARNING'),
                                (None, 'UNKNOWN'), (13, 'WARNING'), (11, 'NORMAL')):
            state = imu_monitor.next_tilt_status(state, None if value is None else (value, 0))
            self.assertEqual(state, expected)


class FreshnessTest(unittest.TestCase):
    def setUp(self):
        self.node = imu_monitor.ImuMonitor.__new__(imu_monitor.ImuMonitor)
        self.node.latest_imu = None
        self.node.last_received_at = None
        self.node.status = None
        self.node.tilt_status = 'UNKNOWN'
        self.node.roll_publisher = Mock()
        self.node.pitch_publisher = Mock()
        self.node.tilt_publisher = Mock()
        self.log = Mock()
        self.timeout = SimpleNamespace(value=2.0)
        logger_patch = patch.object(imu_monitor.ImuMonitor, 'get_logger', return_value=self.log)
        parameter_patch = patch.object(
            imu_monitor.ImuMonitor, 'get_parameter', return_value=self.timeout
        )
        clock_patch = patch.object(imu_monitor.time, 'monotonic', return_value=100.0)
        logger_patch.start()
        parameter_patch.start()
        self.clock = clock_patch.start()
        self.addCleanup(logger_patch.stop)
        self.addCleanup(parameter_patch.stop)
        self.addCleanup(clock_patch.stop)
        self.node.set_status('WAITING', 'No message yet.')

    def test_waiting_is_not_repeated(self):
        self.node.report()
        self.node.report()
        self.assertEqual(self.node.status, 'WAITING')
        self.assertEqual(self.log.info.call_count, 1)

    def test_active_stale_and_recovery(self):
        self.node.on_imu(Imu())
        self.assertEqual(self.node.status, 'ACTIVE')
        self.clock.return_value = 102.0
        self.node.report()  # Equal to the threshold: still recent.
        self.assertIn('angular_velocity', self.log.info.call_args.args[0])
        count = sum('angular_velocity' in call.args[0] for call in self.log.info.call_args_list)
        self.clock.return_value = 102.01
        self.node.report()
        self.node.report()
        self.assertEqual(self.node.status, 'STALE')
        self.assertEqual(
            sum('angular_velocity' in call.args[0] for call in self.log.info.call_args_list), count
        )  # No old measurement output; the UNKNOWN transition is still logged.
        self.assertEqual(self.log.warning.call_count, 1)
        self.node.on_imu(Imu())
        self.assertEqual(self.node.status, 'ACTIVE')
        self.node.report()
        self.assertIn('angular_velocity', self.log.info.call_args.args[0])

    def test_timeout_change_takes_effect(self):
        self.node.on_imu(Imu())
        self.clock.return_value = 103.0
        self.node.report()
        self.assertEqual(self.node.status, 'STALE')
        self.timeout.value = 4.0
        self.node.report()
        self.assertEqual(self.node.status, 'ACTIVE')

    def test_active_does_not_validate_measurements(self):
        msg = Imu()
        msg.linear_acceleration.x = float('nan')
        self.node.on_imu(msg)
        self.node.report()
        self.assertEqual(self.node.status, 'ACTIVE')

    def test_timeout_validation(self):
        for value in (0.0, -1.0, float('nan'), float('inf'), 2):
            with self.subTest(value=value):
                result = self.node.validate_parameters([Parameter('stale_timeout_sec', value=value)])
                self.assertFalse(result.successful)
        result = self.node.validate_parameters([Parameter('stale_timeout_sec', value=0.5)])
        self.assertTrue(result.successful)

    def test_invalid_orientation_does_not_reuse_previous_angles(self):
        msg = Imu()
        msg.orientation.w = 1.0
        self.node.on_imu(msg)
        self.node.report()
        self.assertIn('roll=0.00 deg', self.log.info.call_args.args[0])
        invalid = Imu()
        invalid.orientation.w = 0.0  # Explicit zero quaternion; defaults may vary.
        self.node.on_imu(invalid)
        self.node.report()
        output = self.log.info.call_args.args[0]
        self.assertEqual(self.node.status, 'ACTIVE')
        self.assertIn('orientation=INVALID', output)
        self.assertNotIn('roll=', output)
        self.assertNotIn('pitch=', output)

    def test_stale_orientation_is_not_converted(self):
        msg = Imu()
        msg.orientation.w = 1.0
        self.node.on_imu(msg)
        self.clock.return_value = 103.0
        with patch.object(imu_monitor, 'orientation_to_roll_pitch') as convert:
            self.node.report()
        convert.assert_not_called()
        self.assertEqual(self.node.status, 'STALE')

    def pitch_message(self, pitch):
        msg = Imu()
        msg.orientation.y = math.sin(math.radians(pitch) / 2)
        msg.orientation.w = math.cos(math.radians(pitch) / 2)
        return msg

    def test_outputs_waiting_invalid_stale_and_recovery(self):
        self.node.publish_outputs()
        self.node.roll_publisher.publish.assert_not_called()
        self.node.pitch_publisher.publish.assert_not_called()
        self.assertEqual(self.node.tilt_publisher.publish.call_args.args[0].data, 'UNKNOWN')
        self.node.on_imu(self.pitch_message(-20))
        self.node.publish_outputs()
        self.assertAlmostEqual(self.node.pitch_publisher.publish.call_args.args[0].data, -20)
        self.assertEqual(self.node.tilt_status, 'WARNING')

        for reason in ('invalid', 'unavailable', 'stale'):
            with self.subTest(reason=reason):
                self.node.roll_publisher.reset_mock()
                self.node.pitch_publisher.reset_mock()
                if reason == 'stale':
                    self.clock.return_value += 3.0
                else:
                    msg = self.pitch_message(0)
                    if reason == 'invalid':
                        msg.orientation.w = 0.0
                    else:
                        msg.orientation_covariance[0] = -1.0
                    self.node.on_imu(msg)
                self.node.publish_outputs()
                self.node.roll_publisher.publish.assert_not_called()
                self.node.pitch_publisher.publish.assert_not_called()
                self.assertEqual(self.node.tilt_publisher.publish.call_args.args[0].data, 'UNKNOWN')
                self.node.on_imu(self.pitch_message(13))
                self.node.publish_outputs()
                self.assertEqual(self.node.tilt_status, 'WARNING')
                self.node.on_imu(self.pitch_message(12))
                self.node.publish_outputs()
                self.assertEqual(self.node.tilt_status, 'NORMAL')

    def test_callback_observes_threshold_between_publication_ticks(self):
        for value, expected in ((0, 'NORMAL'), (15, 'WARNING'), (14, 'WARNING')):
            self.node.on_imu(self.pitch_message(value))
            self.assertEqual(self.node.tilt_status, expected)

    def test_gap_between_ticks_resets_hysteresis(self):
        self.node.on_imu(self.pitch_message(0))
        self.clock.return_value += 3.0
        self.node.on_imu(self.pitch_message(13))
        self.assertEqual(self.node.tilt_status, 'WARNING')

    def test_tilt_transition_logs_only_once(self):
        self.node.on_imu(self.pitch_message(20))
        count = self.log.warning.call_count
        for _ in range(10):
            self.node.publish_outputs()
        self.assertEqual(self.log.warning.call_count, count)

    def test_output_rate_validation(self):
        for value in (0.0, -1.0, 0.5, 51.0, float('inf'), float('nan'), 10):
            result = self.node.validate_parameters([Parameter('publish_rate_hz', value=value)])
            self.assertFalse(result.successful)
        for value in (1.0, 10.0, 50.0):
            result = self.node.validate_parameters([Parameter('publish_rate_hz', value=value)])
            self.assertTrue(result.successful)


if __name__ == '__main__':
    unittest.main()
