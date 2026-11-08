"""FireScout FSM ROS-free unit tests for actual node callbacks/control loop.

Mocks only ROS interfaces (rclpy/message classes), then imports the real
firescout_fsm.py. No Gazebo, ROS installation, or sensor simulation needed.

Run from repo root:
    python3 -m unittest discover -s firescout_fs01/test -p 'test_fsm_*.py' -v
"""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'scripts' / 'firescout_fsm.py'


class FakePublisher:
    def __init__(self, topic):
        self.topic = topic
        self.messages = []

    def publish(self, msg):
        self.messages.append(msg)

    @property
    def last(self):
        if not self.messages:
            raise AssertionError(f'No publication on {self.topic}')
        return self.messages[-1]


class FakeLogger:
    def __init__(self):
        self.info_messages = []
        self.warnings = []

    def info(self, message):
        self.info_messages.append(message)

    def warning(self, message):
        self.warnings.append(message)


class FakeNode:
    def __init__(self, name):
        self.node_name = name
        self.parameters = {}
        self.subscriptions = {}
        self.publishers = {}
        self.timers = []
        self.logger = FakeLogger()

    def declare_parameter(self, name, default):
        self.parameters[name] = types.SimpleNamespace(value=default)

    def get_parameter(self, name):
        return self.parameters[name]

    def create_subscription(self, message_type, topic, callback, qos):
        self.subscriptions[topic] = callback
        return callback

    def create_publisher(self, message_type, topic, qos):
        publisher = FakePublisher(topic)
        self.publishers[topic] = publisher
        return publisher

    def create_timer(self, period, callback):
        self.timers.append((period, callback))
        return callback

    def get_logger(self):
        return self.logger


class FakeTwist:
    def __init__(self):
        self.linear = types.SimpleNamespace(x=0.0)
        self.angular = types.SimpleNamespace(z=0.0)


class FakeMessage:
    def __init__(self, data=None):
        self.data = data


class FakeContacts:
    def __init__(self, contacts=None):
        self.contacts = list(contacts or [])


def load_node_module():
    """Import the *real* FSM source with tiny ROS import shims."""
    rclpy = types.ModuleType('rclpy')
    rclpy_node = types.ModuleType('rclpy.node')
    rclpy_node.Node = FakeNode
    rclpy.node = rclpy_node
    rclpy.init = lambda **kwargs: None
    rclpy.spin = lambda node: None
    rclpy.ok = lambda: True
    rclpy.shutdown = lambda: None

    geometry = types.ModuleType('geometry_msgs')
    geometry_msg = types.ModuleType('geometry_msgs.msg')
    geometry_msg.Twist = FakeTwist
    geometry.msg = geometry_msg

    gz_interfaces = types.ModuleType('ros_gz_interfaces')
    gz_msg = types.ModuleType('ros_gz_interfaces.msg')
    gz_msg.Contacts = FakeContacts
    gz_interfaces.msg = gz_msg

    std_msgs = types.ModuleType('std_msgs')
    std_msg = types.ModuleType('std_msgs.msg')
    std_msg.Bool = std_msg.Float32 = std_msg.String = FakeMessage
    std_msgs.msg = std_msg

    stubs = {
        'rclpy': rclpy, 'rclpy.node': rclpy_node,
        'geometry_msgs': geometry, 'geometry_msgs.msg': geometry_msg,
        'ros_gz_interfaces': gz_interfaces, 'ros_gz_interfaces.msg': gz_msg,
        'std_msgs': std_msgs, 'std_msgs.msg': std_msg,
    }
    spec = importlib.util.spec_from_file_location('firescout_fsm_under_test', SOURCE)
    module = importlib.util.module_from_spec(spec)
    # Restrict fake ROS modules to the import, then restore sys.modules.
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


FSM_MODULE = load_node_module()


class TestFSMNode(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        # Patch the module's time reference, not system-wide time.monotonic.
        FSM_MODULE.time = types.SimpleNamespace(monotonic=lambda: self.now)
        self.node = FSM_MODULE.FireScoutFSM()

    def prime(self, lidar='CLEAR', front=3.0, camera='SEARCHING', imu='NORMAL'):
        self.node.on_lidar(FakeMessage(lidar))
        self.node.on_front_distance(FakeMessage(front))
        self.node.on_camera_status(FakeMessage(camera))
        self.node.on_imu(FakeMessage(imu))

    def enable(self):
        self.node.parameters['motion_enabled'].value = True

    def tick(self):
        self.node.control_loop()
        cmd = self.node.publishers['/cmd_vel'].last
        return (cmd.linear.x, cmd.angular.z)

    def status(self):
        return self.node.publishers['/firescout/fsm/state'].last.data

    def events(self):
        return [message.data for message in self.node.publishers['/firescout/fsm/event'].messages]

    def test_starts_disabled_and_waiting(self):
        self.assertFalse(self.node.get_parameter('motion_enabled').value)
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'WAIT_SENSORS')

    def test_exposes_expected_topics(self):
        expected = {
            '/firescout/lidar/status', '/firescout/lidar/open_side',
            '/firescout/lidar/front_m', '/firescout/lidar/left_m',
            '/firescout/lidar/right_m', '/firescout/imu/tilt_status',
            '/firescout/camera/status', '/firescout/camera/hazard_detected',
            '/bumper/contacts',
        }
        self.assertEqual(set(self.node.subscriptions), expected)
        self.assertIn('/cmd_vel', self.node.publishers)
        self.assertEqual(self.node.timers[0][0], 0.1)

    def test_disabled_stays_zero_even_when_explore(self):
        self.prime()
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'EXPLORE')

    def test_explore_forward_when_enabled(self):
        self.prime()
        self.enable()
        self.assertEqual(self.tick(), (0.04, 0.0))
        self.assertEqual(self.status(), 'EXPLORE')

    def test_disabling_motion_stops_on_next_control_tick(self):
        self.prime()
        self.enable()
        self.assertEqual(self.tick(), (0.04, 0.0))
        self.node.parameters['motion_enabled'].value = False
        self.assertEqual(self.tick(), (0.0, 0.0))

    def test_warning_moves_slowly_at_safe_distance(self):
        self.prime(lidar='WARNING', front=0.95)
        self.enable()
        self.assertEqual(self.tick(), (0.02, 0.0))
        self.assertEqual(self.status(), 'CAUTION')

    def test_warning_stops_below_extra_caution_margin(self):
        self.prime(lidar='WARNING', front=0.75)
        self.enable()
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'CAUTION')

    def test_avoid_turns_left_on_clear_left(self):
        self.prime(lidar='DANGER', front=0.5)
        self.node.on_open_side(FakeMessage('LEFT'))
        self.node.on_left_distance(FakeMessage(1.4))
        self.enable()
        self.assertEqual(self.tick(), (0.0, +0.25))
        self.assertEqual(self.status(), 'AVOID')
        self.assertEqual(self.node.avoid_direction, +1)

    def test_avoid_turns_right_on_clear_right(self):
        self.prime(lidar='DANGER', front=0.5)
        self.node.on_open_side(FakeMessage('RIGHT'))
        self.node.on_right_distance(FakeMessage(2.0))
        self.enable()
        self.assertEqual(self.tick(), (0.0, -0.25))
        self.assertEqual(self.status(), 'AVOID')

    def test_avoid_no_open_side_stops(self):
        self.prime(lidar='DANGER', front=0.5)
        self.enable()
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'AVOID')

    def test_avoid_side_below_threshold_stops(self):
        self.prime(lidar='DANGER', front=0.5)
        self.node.on_open_side(FakeMessage('LEFT'))
        self.node.on_left_distance(FakeMessage(0.7))
        self.enable()
        self.assertEqual(self.tick(), (0.0, 0.0))

    def test_avoid_front_too_close_stops_rotation(self):
        self.prime(lidar='DANGER', front=0.25)
        self.node.on_open_side(FakeMessage('RIGHT'))
        self.node.on_right_distance(FakeMessage(1.8))
        self.enable()
        self.assertEqual(self.tick(), (0.0, 0.0))

    def test_turn_direction_does_not_flip_mid_avoid(self):
        self.prime(lidar='DANGER', front=0.5)
        self.node.on_open_side(FakeMessage('LEFT'))
        self.node.on_left_distance(FakeMessage(2.0))
        self.node.on_right_distance(FakeMessage(2.0))
        self.enable()
        self.assertEqual(self.tick(), (0.0, +0.25))
        self.now = 100.2
        self.prime(lidar='DANGER', front=0.55)
        self.node.on_open_side(FakeMessage('RIGHT'))
        self.node.on_right_distance(FakeMessage(3.0))
        self.assertEqual(self.tick(), (0.0, +0.25))

    def test_avoid_stays_until_front_clearance_is_reached(self):
        self.prime(lidar='DANGER', front=0.5)
        self.node.on_open_side(FakeMessage('LEFT'))
        self.node.on_left_distance(FakeMessage(1.7))
        self.enable()
        self.assertEqual(self.tick(), (0.0, +0.25))
        self.now = 101.0
        self.prime(lidar='CLEAR', front=1.20)
        self.node.on_left_distance(FakeMessage(1.7))
        self.assertEqual(self.tick(), (0.0, +0.25))
        self.assertEqual(self.status(), 'AVOID')

    def test_avoid_completes_after_clearance_and_min_turn(self):
        self.prime(lidar='DANGER', front=0.5)
        self.node.on_open_side(FakeMessage('LEFT'))
        self.node.on_left_distance(FakeMessage(1.9))
        self.enable()
        self.assertEqual(self.tick(), (0.0, +0.25))
        self.now = 101.0
        self.prime(lidar='CLEAR', front=2.5)
        self.assertEqual(self.tick(), (0.04, 0.0))
        self.assertEqual(self.status(), 'EXPLORE')
        self.assertEqual(self.node.avoid_direction, 0)

    def test_avoid_still_turns_before_min_duration(self):
        self.prime(lidar='DANGER', front=0.5)
        self.node.on_open_side(FakeMessage('LEFT'))
        self.node.on_left_distance(FakeMessage(1.8))
        self.enable()
        self.assertEqual(self.tick(), (0.0, +0.25))
        self.now = 100.25
        self.prime(lidar='CLEAR', front=2.0)
        self.node.on_left_distance(FakeMessage(1.8))
        self.assertEqual(self.tick(), (0.0, +0.25))
        self.assertEqual(self.status(), 'AVOID')

    def test_avoid_stale_side_halts_rotation(self):
        self.prime(lidar='DANGER', front=0.5)
        self.node.on_open_side(FakeMessage('LEFT'))
        self.node.on_left_distance(FakeMessage(1.9))
        self.enable()
        self.assertEqual(self.tick(), (0.0, +0.25))
        self.now = 101.1
        self.prime(lidar='DANGER', front=0.5)
        self.assertEqual(self.tick(), (0.0, 0.0))

    def test_avoid_timeout_triggers_latched_safe_stop(self):
        self.prime(lidar='DANGER', front=0.5)
        self.node.on_open_side(FakeMessage('RIGHT'))
        self.node.on_right_distance(FakeMessage(2.5))
        self.enable()
        self.assertEqual(self.tick(), (0.0, -0.25))
        self.now = 112.1
        self.prime(lidar='DANGER', front=0.5)
        self.node.on_right_distance(FakeMessage(2.5))
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertTrue(self.node.avoid_fault_latched)
        self.assertEqual(self.status(), 'SAFE_STOP')
        self.assertTrue(any('avoidance timeout' in event for event in self.events()))
        self.now = 112.2
        self.prime(lidar='CLEAR', front=3.0)
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'SAFE_STOP')

    def test_red_detection_latches_hazard_stop(self):
        self.prime(camera='DETECTED')
        self.node.on_hazard(FakeMessage(True))
        self.enable()
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'HAZARD_STOP')
        self.now = 100.2
        self.prime(camera='SEARCHING')
        self.node.on_hazard(FakeMessage(False))
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'HAZARD_STOP')

    def test_stale_hazard_flag_does_not_trigger_false_latch(self):
        self.prime(camera='DETECTED')
        self.node.on_hazard(FakeMessage(True))
        self.node.last_hazard = 96.0
        self.enable()
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertNotEqual(self.status(), 'HAZARD_STOP')
        self.assertFalse(self.node.hazard_latched)

    def test_contact_latches_recover_and_reports_contact(self):
        self.prime()
        self.node.on_contact(FakeContacts([object()]))
        self.enable()
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'RECOVER')
        self.assertEqual(self.node.publishers['/firescout/bumper/status'].last.data, 'CONTACT')
        self.assertEqual(self.node.publishers['/firescout/bumper/contact_value'].last.data, 1.0)
        self.now = 100.2
        self.prime()
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'RECOVER')

    def test_empty_contact_is_ignored(self):
        self.prime()
        self.node.on_contact(FakeContacts([]))
        self.enable()
        self.assertEqual(self.tick(), (0.04, 0.0))
        self.assertEqual(self.node.publishers['/firescout/bumper/status'].last.data, 'CLEAR')

    def test_contact_overrides_hazard_latch(self):
        self.prime()
        self.node.hazard_latched = True
        self.node.on_contact(FakeContacts([object()]))
        self.enable()
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'RECOVER')

    def test_imu_abnormal_safe_stop(self):
        self.prime(imu='TILT')
        self.enable()
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'SAFE_STOP')

    def test_imu_recovers_after_normal_message(self):
        self.prime(imu='TILT')
        self.enable()
        self.tick()
        self.now = 100.3
        self.prime(imu='NORMAL')
        self.assertEqual(self.tick(), (0.04, 0.0))
        self.assertEqual(self.status(), 'EXPLORE')

    def test_camera_stale_status_safe_stop(self):
        self.prime(camera='STALE')
        self.enable()
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'SAFE_STOP')

    def test_unknown_camera_status_safe_stop(self):
        self.prime(camera='UNKNOWN')
        self.enable()
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'SAFE_STOP')

    def test_camera_timestamp_timeout_safe_stop(self):
        self.prime()
        self.enable()
        self.now = 103.1
        self.node.on_lidar(FakeMessage('CLEAR'))
        self.node.on_front_distance(FakeMessage(3.0))
        self.node.on_imu(FakeMessage('NORMAL'))
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'SAFE_STOP')

    def test_lidar_timestamp_timeout_safe_stop(self):
        self.prime()
        self.enable()
        self.now = 102.6
        self.node.on_camera_status(FakeMessage('SEARCHING'))
        self.node.on_front_distance(FakeMessage(3.0))
        self.node.on_imu(FakeMessage('NORMAL'))
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'SAFE_STOP')

    def test_front_range_timeout_safe_stop(self):
        self.prime()
        self.enable()
        self.now = 101.1
        self.node.on_camera_status(FakeMessage('SEARCHING'))
        self.node.on_lidar(FakeMessage('CLEAR'))
        self.node.on_imu(FakeMessage('NORMAL'))
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'SAFE_STOP')

    def test_missing_initial_camera_waits(self):
        self.node.on_lidar(FakeMessage('CLEAR'))
        self.node.on_front_distance(FakeMessage(3.0))
        self.node.on_imu(FakeMessage('NORMAL'))
        self.enable()
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'WAIT_SENSORS')

    def test_invalid_range_safe_stop(self):
        self.prime(front=float('nan'))
        self.enable()
        self.assertEqual(self.tick(), (0.0, 0.0))
        self.assertEqual(self.status(), 'SAFE_STOP')

    def test_status_event_published_only_on_transition(self):
        self.prime()
        self.tick()
        self.assertEqual(len(self.events()), 1)
        self.assertEqual(self.events()[0], 'WAIT_SENSORS -> EXPLORE')
        self.tick()
        self.assertEqual(len(self.events()), 1)
        self.node.on_lidar(FakeMessage('WARNING'))
        self.node.on_front_distance(FakeMessage(0.95))
        self.tick()
        self.assertEqual(self.events()[-1], 'EXPLORE -> CAUTION')


if __name__ == '__main__':
    unittest.main(verbosity=2)
