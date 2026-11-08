#!/usr/bin/env python3
"""FireScout FS-01 - conservative seven-state sensor-based FSM.

Motion is DISABLED by default. Native Ubuntu validation is required before demo.
States: WAIT_SENSORS, EXPLORE, CAUTION, AVOID, RECOVER,
        HAZARD_STOP, SAFE_STOP.
"""

import math
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from ros_gz_interfaces.msg import Contacts
from std_msgs.msg import Bool, Float32, String


# Pure policy: returns (linear.x [m/s], angular.z [rad/s]).
# Kept independent of ROS to make its behavior easy to unit test.
def motion_policy(state, enabled, camera_status, front_m, front_fresh,
                  turn_direction=0, turn_side_m=None, turn_side_fresh=False):
    if not enabled or camera_status != 'SEARCHING' or not front_fresh:
        return 0.0, 0.0
    if front_m is None or not math.isfinite(front_m) or front_m < 0.0:
        return 0.0, 0.0

    if state == 'EXPLORE' and front_m > 1.50:
        return 0.04, 0.0
    if state == 'CAUTION' and front_m > 0.80:
        return 0.02, 0.0
    if state == 'AVOID':
        # In-place turn only if front and selected lateral sector are usable.
        # Sector clearance does not guarantee full-body collision-free turning.
        if (front_m >= 0.30 and turn_direction in (-1, 1)
                and turn_side_fresh and turn_side_m is not None
                and math.isfinite(turn_side_m) and turn_side_m > 0.90):
            return 0.0, 0.25 * turn_direction
    return 0.0, 0.0


class FireScoutFSM(Node):
    def __init__(self):
        super().__init__('firescout_fsm')
        self.declare_parameter('motion_enabled', False)

        self.state = 'WAIT_SENSORS'
        self.lidar_status = None
        self.open_side = None
        self.front_distance = None
        self.left_distance = None
        self.right_distance = None
        self.imu_status = None
        self.camera_status = None
        self.hazard_detected = False
        self.hazard_latched = False
        self.contact_triggered = False
        self.avoid_fault_latched = False

        self.last_lidar = None
        self.last_open_side = None
        self.last_front_distance = None
        self.last_left_distance = None
        self.last_right_distance = None
        self.last_imu = None
        self.last_camera = None
        self.last_hazard = None
        self.avoid_direction = 0  # +1 LEFT, -1 RIGHT
        self.avoid_started = None  # Starts when a turn command is actually sent
        self.avoid_clearance_m = 1.35
        self.max_avoid_sec = 12.0

        self.create_subscription(String, '/firescout/lidar/status', self.on_lidar, 10)
        self.create_subscription(String, '/firescout/lidar/open_side', self.on_open_side, 10)
        self.create_subscription(Float32, '/firescout/lidar/front_m', self.on_front_distance, 10)
        self.create_subscription(Float32, '/firescout/lidar/left_m', self.on_left_distance, 10)
        self.create_subscription(Float32, '/firescout/lidar/right_m', self.on_right_distance, 10)
        self.create_subscription(String, '/firescout/imu/tilt_status', self.on_imu, 10)
        self.create_subscription(String, '/firescout/camera/status', self.on_camera_status, 10)
        self.create_subscription(Bool, '/firescout/camera/hazard_detected', self.on_hazard, 10)
        self.create_subscription(Contacts, '/bumper/contacts', self.on_contact, 10)

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.state_pub = self.create_publisher(String, '/firescout/fsm/state', 10)
        self.event_pub = self.create_publisher(String, '/firescout/fsm/event', 10)
        self.bumper_pub = self.create_publisher(String, '/firescout/bumper/status', 10)
        self.bumper_value_pub = self.create_publisher(Float32, '/firescout/bumper/contact_value', 10)
        self.timer = self.create_timer(0.1, self.control_loop)
        self.get_logger().info(
            f'FireScout FSM started; motion_enabled={self.get_parameter("motion_enabled").value}'
        )

    def on_lidar(self, msg):
        self.lidar_status = msg.data
        self.last_lidar = time.monotonic()

    def on_open_side(self, msg):
        self.open_side = msg.data
        self.last_open_side = time.monotonic()

    def on_front_distance(self, msg):
        self.front_distance = msg.data
        self.last_front_distance = time.monotonic()

    def on_left_distance(self, msg):
        self.left_distance = msg.data
        self.last_left_distance = time.monotonic()

    def on_right_distance(self, msg):
        self.right_distance = msg.data
        self.last_right_distance = time.monotonic()

    def on_imu(self, msg):
        self.imu_status = msg.data
        self.last_imu = time.monotonic()

    def on_camera_status(self, msg):
        self.camera_status = msg.data
        self.last_camera = time.monotonic()

    def on_hazard(self, msg):
        self.hazard_detected = bool(msg.data)
        self.last_hazard = time.monotonic()

    def on_contact(self, msg):
        if msg.contacts:
            self.contact_triggered = True

    @staticmethod
    def is_fresh(timestamp, now, timeout):
        return timestamp is not None and 0.0 <= now - timestamp <= timeout

    @staticmethod
    def age_text(timestamp, now):
        return 'none' if timestamp is None else f'{now - timestamp:.2f}s'

    def decide_state(self, now):
        # Fatal/latching conditions override ordinary navigation.
        if self.contact_triggered:
            return 'RECOVER'
        if self.hazard_latched:
            return 'HAZARD_STOP'
        if self.avoid_fault_latched:
            return 'SAFE_STOP'

        if any(ts is None for ts in (self.last_lidar, self.last_imu, self.last_camera)):
            return 'WAIT_SENSORS'
        if not self.is_fresh(self.last_lidar, now, 2.5):
            return 'SAFE_STOP'
        if not self.is_fresh(self.last_imu, now, 2.5):
            return 'SAFE_STOP'
        if not self.is_fresh(self.last_camera, now, 3.0):
            return 'SAFE_STOP'
        if self.imu_status != 'NORMAL':
            return 'SAFE_STOP'
        if self.camera_status not in ('SEARCHING', 'DETECTED'):
            return 'SAFE_STOP'
        if self.lidar_status not in ('CLEAR', 'WARNING', 'DANGER'):
            return 'SAFE_STOP'

        # Only fresh hazard information may result in a mission-complete latch.
        if (self.camera_status == 'DETECTED' and self.hazard_detected
                and self.is_fresh(self.last_hazard, now, 3.0)):
            self.hazard_latched = True
            return 'HAZARD_STOP'

        # Do not use an old front reading to choose or continue a maneuver.
        if not self.is_fresh(self.last_front_distance, now, 1.0):
            return 'SAFE_STOP'
        if (self.front_distance is None
                or not math.isfinite(self.front_distance)
                or self.front_distance < 0.0):
            return 'SAFE_STOP'

        # Avoid turning back into the obstacle as soon as front range rises to 0.7m.
        # Leave AVOID only when front is >1.35m and enough turn time has elapsed.
        if self.state == 'AVOID':
            turning_enough = (self.avoid_started is None or
                              now - self.avoid_started >= 0.6)
            if not (self.front_distance > self.avoid_clearance_m and turning_enough):
                return 'AVOID'

        if self.lidar_status == 'DANGER':
            return 'AVOID'
        # Enter slow mode at the existing EXPLORE clearance margin too.
        # LiDAR remains CLEAR down to 1.20 m; do not strand EXPLORE at 1.50 m.
        if self.lidar_status == 'WARNING' or self.front_distance <= 1.50:
            return 'CAUTION'
        return 'EXPLORE'

    def choose_turn_side(self, now):
        # open_side alone is NOT enough: the monitor chooses LEFT even when both
        # lateral sectors are unknown. Require a fresh measured side clearance.
        if not self.is_fresh(self.last_open_side, now, 1.0):
            return 0
        if self.open_side == 'LEFT' and self.is_fresh(self.last_left_distance, now, 1.0):
            return +1
        if self.open_side == 'RIGHT' and self.is_fresh(self.last_right_distance, now, 1.0):
            return -1
        return 0

    def side_data(self, now):
        if self.avoid_direction == +1:
            return self.left_distance, self.is_fresh(self.last_left_distance, now, 1.0)
        if self.avoid_direction == -1:
            return self.right_distance, self.is_fresh(self.last_right_distance, now, 1.0)
        return None, False

    def control_loop(self):
        now = time.monotonic()
        new_state = self.decide_state(now)

        if new_state != self.state:
            event = f'{self.state} -> {new_state}'
            if new_state == 'SAFE_STOP':
                event += (f' | lidar={self.lidar_status} ({self.age_text(self.last_lidar, now)})'
                          f' | front={self.front_distance}'
                          f' ({self.age_text(self.last_front_distance, now)})'
                          f' | imu={self.imu_status} ({self.age_text(self.last_imu, now)})'
                          f' | camera={self.camera_status} ({self.age_text(self.last_camera, now)})')
            self.get_logger().info(event)
            self.event_pub.publish(String(data=event))
            self.state = new_state
            if new_state != 'AVOID':
                self.avoid_direction = 0
                self.avoid_started = None

        # State is published after the motion safety checks below, because
        # an AVOID timeout can change it to SAFE_STOP within this same tick.
        self.bumper_pub.publish(String(data='CONTACT' if self.contact_triggered else 'CLEAR'))
        self.bumper_value_pub.publish(Float32(data=1.0 if self.contact_triggered else 0.0))

        enabled = bool(self.get_parameter('motion_enabled').value)
        if enabled and self.state == 'AVOID' and self.avoid_direction == 0:
            self.avoid_direction = self.choose_turn_side(now)

        side_m, side_fresh = self.side_data(now)
        lin, ang = motion_policy(
            self.state, enabled, self.camera_status,
            self.front_distance, self.is_fresh(self.last_front_distance, now, 1.0),
            self.avoid_direction, side_m, side_fresh)

        # Timeout is measured in wall time spent in the turning maneuver.
        if not enabled or self.state != 'AVOID':
            self.avoid_started = None
            if not enabled:
                self.avoid_direction = 0
        elif ang != 0.0:
            if self.avoid_started is None:
                self.avoid_started = now
            elif now - self.avoid_started > self.max_avoid_sec:
                self.avoid_fault_latched = True
                self.state = 'SAFE_STOP'
                self.event_pub.publish(String(data='AVOID -> SAFE_STOP | avoidance timeout'))
                self.get_logger().warning('AVOID timeout: SAFE_STOP latched until restart')
                self.avoid_direction = 0
                self.avoid_started = None
                lin, ang = 0.0, 0.0

        cmd = Twist()
        cmd.linear.x = float(lin)
        cmd.angular.z = float(ang)
        self.state_pub.publish(String(data=self.state))
        self.cmd_pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = FireScoutFSM()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.cmd_pub.publish(Twist())
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
