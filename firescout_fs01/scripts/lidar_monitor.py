#!/usr/bin/env python3
"""Read /scan, measure front/left/right clearance and publish an obstacle status.

Outputs (for rqt_plot and for the behaviour node):
  /firescout/lidar/front_m    Float32  nearest obstacle ahead       (-20..+20 deg)
  /firescout/lidar/left_m     Float32  nearest obstacle on the left (+60..+120 deg)
  /firescout/lidar/right_m    Float32  nearest obstacle on the right (-120..-60 deg)
  /firescout/lidar/status     String   WAITING / STALE / NO_DATA / CLEAR / WARNING / DANGER
  /firescout/lidar/open_side  String   LEFT or RIGHT, whichever side has more room

Angles follow ROS convention: 0 deg is straight ahead (+X), positive is to the left.
"""

import math
import signal
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float32, String


# (lowest angle, highest angle) in degrees for each sector.
SECTORS = {
    'front': (-20.0, 20.0),
    'left': (60.0, 120.0),
    'right': (-120.0, -60.0),
}


def beam_angle_deg(msg, index):
    """Angle of beam `index` in degrees, wrapped to [-180, 180)."""
    angle = msg.angle_min + index * msg.angle_increment
    return math.degrees(math.atan2(math.sin(angle), math.cos(angle)))


def sector_distance(msg, low_deg, high_deg):
    """Nearest valid range inside [low_deg, high_deg].

    Returns the distance in metres, math.inf when every beam in the sector saw
    nothing (+inf = no surface within range), or None when the sector has no
    usable beam at all (NaN, below range_min, empty scan).
    """
    nearest = None
    saw_open_space = False
    for index, distance in enumerate(msg.ranges):
        if not low_deg <= beam_angle_deg(msg, index) <= high_deg:
            continue
        if math.isfinite(distance) and msg.range_min <= distance <= msg.range_max:
            nearest = distance if nearest is None else min(nearest, distance)
        elif distance == math.inf or (math.isfinite(distance) and distance > msg.range_max):
            saw_open_space = True
        # NaN, -inf and readings below range_min are not measurements; skip them.
    if nearest is not None:
        return nearest
    if saw_open_space:
        return math.inf
    return None


def obstacle_status(front_m, danger_m, warning_m):
    """Classify the distance ahead."""
    if front_m is None:
        return 'NO_DATA'
    if front_m < danger_m:
        return 'DANGER'
    if front_m < warning_m:
        return 'WARNING'
    return 'CLEAR'


def more_open_side(left_m, right_m):
    """LEFT or RIGHT, whichever has more room. Unknown sides count as blocked."""
    left = -1.0 if left_m is None else left_m
    right = -1.0 if right_m is None else right_m
    return 'LEFT' if left >= right else 'RIGHT'


class LidarMonitor(Node):
    def __init__(self):
        super().__init__('lidar_monitor')
        self.declare_parameter('danger_distance', 0.70)
        self.declare_parameter('warning_distance', 1.20)
        self.declare_parameter('stale_timeout_sec', 1.0)

        self.latest_scan = None
        self.last_received_at = None
        self.status = None

        self.distance_publishers = {
            name: self.create_publisher(Float32, f'/firescout/lidar/{name}_m', 10)
            for name in SECTORS
        }
        self.status_publisher = self.create_publisher(String, '/firescout/lidar/status', 10)
        self.side_publisher = self.create_publisher(String, '/firescout/lidar/open_side', 10)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)

        # Steady clock: freshness checks keep running even if simulation time pauses.
        steady = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.1, self.publish_outputs, clock=steady)
        self.create_timer(1.0, self.report, clock=steady)
        self.set_status('WAITING')

    def on_scan(self, msg):
        self.latest_scan = msg
        self.last_received_at = time.monotonic()

    def set_status(self, status):
        if status == self.status:
            return
        self.status = status
        message = f'status -> {status}'
        if status in ('STALE', 'DANGER', 'NO_DATA'):
            self.get_logger().warning(message)
        else:
            self.get_logger().info(message)

    def measure(self):
        """Return {sector: distance} from a fresh scan, or None."""
        if self.last_received_at is None:
            self.set_status('WAITING')
            return None
        if time.monotonic() - self.last_received_at > self.get_parameter('stale_timeout_sec').value:
            # Never report old distances as if they were current.
            self.set_status('STALE')
            return None
        distances = {
            name: sector_distance(self.latest_scan, low, high)
            for name, (low, high) in SECTORS.items()
        }
        self.set_status(obstacle_status(
            distances['front'],
            self.get_parameter('danger_distance').value,
            self.get_parameter('warning_distance').value,
        ))
        return distances

    def publish_outputs(self):
        distances = self.measure()
        self.status_publisher.publish(String(data=self.status))
        if distances is None:
            return
        for name, distance in distances.items():
            if distance is None:
                continue
            # rqt_plot cannot draw inf, so open space is plotted at the sensor's max range.
            value = self.latest_scan.range_max if math.isinf(distance) else distance
            self.distance_publishers[name].publish(Float32(data=float(value)))
        self.side_publisher.publish(String(data=more_open_side(distances['left'], distances['right'])))

    def report(self):
        distances = self.measure()
        if distances is None:
            return

        def text(distance):
            if distance is None:
                return 'n/a'
            return 'open' if math.isinf(distance) else f'{distance:.2f} m'

        self.get_logger().info(
            f'{self.status} | front={text(distances["front"])} '
            f'left={text(distances["left"])} right={text(distances["right"])} | '
            f'more room: {more_open_side(distances["left"], distances["right"])}'
        )


def stop_on_sigterm(signum, frame):
    raise KeyboardInterrupt


def main(args=None):
    # rclpy's own signal handler shuts the context down while spin() is still
    # running, which prints an RCLError traceback on Ctrl+C. Handle signals here.
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGTERM, stop_on_sigterm)
    node = LidarMonitor()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
