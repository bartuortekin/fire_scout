#!/usr/bin/env python3
"""Publish fresh IMU angles and demo tilt status; log measurements once per second."""

import math
import time

import rclpy
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32, String


# Allow 0.1% norm error for rounding; reject larger errors rather than hiding them.
QUATERNION_NORM_TOLERANCE = 1e-3
QUATERNION_MIN_NORM = 1e-12


def orientation_to_roll_pitch(msg):
    """Return ((roll_deg, pitch_deg), validity), or (None, reason).

    ROS quaternion order is x, y, z, w. Use R = Rz(yaw) Ry(pitch) Rx(roll).
    At pitch +/-90 degrees, roll and yaw cannot be determined independently.
    Covariance describes uncertainty; an all-zero covariance means unknown.
    """
    if msg.orientation_covariance[0] == -1:
        return None, 'UNAVAILABLE (orientation_covariance[0] = -1)'

    q = msg.orientation
    components = (q.x, q.y, q.z, q.w)
    if not all(math.isfinite(value) for value in components):
        return None, 'INVALID (non-finite quaternion component)'

    norm = math.hypot(*components)
    if norm <= QUATERNION_MIN_NORM:
        return None, 'INVALID (quaternion norm near zero)'
    if abs(norm - 1.0) > QUATERNION_NORM_TOLERANCE:
        return None, f'INVALID (quaternion norm {norm:.6g} outside tolerance)'

    x, y, z, w = (value / norm for value in components)
    roll = math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
    sin_pitch = 2.0 * (w * y - z * x)
    # Rounding can place the argument slightly outside asin's [-1, 1] domain.
    pitch = math.asin(max(-1.0, min(1.0, sin_pitch)))
    validity = 'VALID'
    if all(value == 0.0 for value in msg.orientation_covariance):
        validity += ' (uncertainty unknown)'
    return (math.degrees(roll), math.degrees(pitch)), validity


def next_tilt_status(previous, angles):
    """Demo hysteresis on max(|roll|, |pitch|), not the total physical tilt angle."""
    if angles is None:
        return 'UNKNOWN'
    metric = max(abs(angles[0]), abs(angles[1]))
    # Ignore conversion roundoff at exact thresholds (e.g. 14.999999999999998).
    if metric >= 15.0 or math.isclose(metric, 15.0, rel_tol=0.0, abs_tol=1e-9):
        return 'WARNING'
    if metric <= 12.0 or math.isclose(metric, 12.0, rel_tol=0.0, abs_tol=1e-9):
        return 'NORMAL'
    return previous if previous in ('NORMAL', 'WARNING') else 'WARNING'


class ImuMonitor(Node):
    def __init__(self):
        super().__init__('imu_monitor')
        self.add_on_set_parameters_callback(self.validate_parameters)
        self.declare_parameter('stale_timeout_sec', 2.0)
        self.declare_parameter(
            'publish_rate_hz', 10.0,
            ParameterDescriptor(
                read_only=True,
                description='Output rate in Hz (1-50); set at startup.',
            ),
        )
        # Read the timeout on each check so ros2 param set also takes effect.
        self.latest_imu = None
        self.last_received_at = None
        self.status = None
        self.tilt_status = None
        self.set_status('WAITING', 'No /imu/data message received yet.')
        self.set_tilt_status('UNKNOWN')
        self.roll_publisher = self.create_publisher(Float32, '/firescout/imu/roll_deg', 1)
        self.pitch_publisher = self.create_publisher(Float32, '/firescout/imu/pitch_deg', 1)
        self.tilt_publisher = self.create_publisher(String, '/firescout/imu/tilt_status', 1)
        self.subscription = self.create_subscription(
            Imu, '/imu/data', self.on_imu, qos_profile_sensor_data
        )
        # Do not let a paused /clock stop freshness checks.
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.timer = self.create_timer(1.0, self.report, clock=self.steady_clock)
        self.publish_timer = self.create_timer(
            1.0 / self.get_parameter('publish_rate_hz').value,
            self.publish_outputs, clock=self.steady_clock,
        )

    @staticmethod
    def validate_parameters(parameters):
        for parameter in parameters:
            if parameter.name == 'stale_timeout_sec':
                value = parameter.value
                if not isinstance(value, float) or not math.isfinite(value) or value <= 0:
                    return SetParametersResult(
                        successful=False,
                        reason='stale_timeout_sec must be a finite positive double.',
                    )
            if parameter.name == 'publish_rate_hz':
                value = parameter.value
                if not isinstance(value, float) or not math.isfinite(value) or not 1.0 <= value <= 50.0:
                    return SetParametersResult(
                        successful=False,
                        reason='publish_rate_hz must be a finite double between 1 and 50.',
                    )
        return SetParametersResult(successful=True)

    def on_imu(self, msg):
        # A gap may occur entirely between timer ticks. Reset hysteresis in that case.
        now = time.monotonic()
        if self.last_received_at is not None:
            if now - self.last_received_at > self.get_parameter('stale_timeout_sec').value:
                self.set_tilt_status('UNKNOWN')
        self.latest_imu = msg
        self.last_received_at = now
        self.set_status('ACTIVE', 'Receiving /imu/data; orientation checked separately.')
        # Observe every received sample, even if the plot publishes more slowly.
        self.current_measurement()

    def set_tilt_status(self, status):
        if status == self.tilt_status:
            return
        self.tilt_status = status
        message = f'tilt_status={status} (demo thresholds: WARNING >=15 deg, NORMAL <=12 deg)'
        if status == 'WARNING':
            self.get_logger().warning(message)
        else:
            self.get_logger().info(message)

    def set_status(self, status, detail):
        if status == self.status:
            return
        self.status = status
        log = self.get_logger()
        if status == 'STALE':
            log.warning(f'{status}: {detail}')
        else:
            log.info(f'{status}: {detail}')

    def current_measurement(self):
        if self.last_received_at is None:
            self.set_tilt_status('UNKNOWN')
            return None, 'UNAVAILABLE (waiting for data)'

        timeout = self.get_parameter('stale_timeout_sec').value
        age = time.monotonic() - self.last_received_at
        if age > timeout:
            self.set_status(
                'STALE',
                f'Last /imu/data received {age:.1f} s ago '
                f'(timeout {timeout:.1f} s); measurements withheld.',
            )
            self.set_tilt_status('UNKNOWN')
            return None, 'UNAVAILABLE (stale data)'

        self.set_status('ACTIVE', 'Recent /imu/data reception; orientation checked separately.')
        # Only fresh messages reach this conversion. Never reuse previous angles.
        angles, validity = orientation_to_roll_pitch(self.latest_imu)
        self.set_tilt_status(next_tilt_status(self.tilt_status, angles))
        return angles, validity

    def publish_outputs(self):
        angles, _ = self.current_measurement()
        if angles is not None:
            self.roll_publisher.publish(Float32(data=angles[0]))
            self.pitch_publisher.publish(Float32(data=angles[1]))
        # Publish UNKNOWN too, so consumers can distinguish missing angles from NORMAL.
        self.tilt_publisher.publish(String(data=self.tilt_status))

    def report(self):
        angles, validity = self.current_measurement()
        if self.status != 'ACTIVE':
            return
        orientation_text = f'orientation={validity}'
        if angles is not None:
            roll, pitch = angles
            orientation_text += f' | roll={roll:.2f} deg, pitch={pitch:.2f} deg'
        angular = self.latest_imu.angular_velocity
        accel = self.latest_imu.linear_acceleration
        self.get_logger().info(
            f'ACTIVE | tilt_status={self.tilt_status} | {orientation_text} | '
            f'angular_velocity [rad/s]: x={angular.x:.3f}, '
            f'y={angular.y:.3f}, z={angular.z:.3f} | '
            f'linear_acceleration [m/s^2]: x={accel.x:.3f}, '
            f'y={accel.y:.3f}, z={accel.z:.3f}'
        )


def main(args=None):
    rclpy.init(args=args)
    node = ImuMonitor()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
