#!/usr/bin/env python3

"""FireScout FS-01 - Sensor-based finite state machine."""

import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from ros_gz_interfaces.msg import Contacts
from std_msgs.msg import Bool, Float32, String


class FireScoutFSM(Node):

    def __init__(self):
        super().__init__('firescout_fsm')

        self.state = 'WAIT_SENSORS'
        self.start_time = time.monotonic()

        self.lidar_status = None
        self.open_side = None
        self.front_distance = None
        self.last_front_distance = None
        self.imu_status = None
        self.camera_status = None
        self.hazard_detected = False
        self.hazard_latched = False
        self.contact_triggered = False
        self.declare_parameter('motion_enabled', False) #hareket başlangıçta kapalı olacak.

        self.last_lidar = None
        self.last_imu = None
        self.last_camera = None

        self.create_subscription(
            String, '/firescout/lidar/status',
            self.on_lidar, 10
        )
        self.create_subscription(
            String, '/firescout/lidar/open_side',
            self.on_open_side, 10
        )
        self.create_subscription(
            Float32, '/firescout/lidar/front_m',
            self.on_front_distance, 10
        )
        self.create_subscription(
            String, '/firescout/imu/tilt_status',
            self.on_imu, 10
        )
        self.create_subscription(
            String, '/firescout/camera/status',
            self.on_camera_status, 10
        )
        self.create_subscription(
            Bool, '/firescout/camera/hazard_detected',
            self.on_hazard, 10
        )
        self.create_subscription(
            Contacts, '/bumper/contacts',
            self.on_contact, 10
        )

        self.cmd_pub = self.create_publisher(
            Twist, '/cmd_vel', 10
        )
        self.state_pub = self.create_publisher(
            String, '/firescout/fsm/state', 10
        )
        self.event_pub = self.create_publisher(
            String, '/firescout/fsm/event', 10
        )
        self.bumper_pub = self.create_publisher(
            String, '/firescout/bumper/status', 10
        )
        self.bumper_value_pub = self.create_publisher(
            Float32, '/firescout/bumper/contact_value', 10
        )

        self.timer = self.create_timer(0.1, self.control_loop)

        self.get_logger().info(
            'FireScout FSM started - motion disabled for initial testing.'
        )

    def on_lidar(self, msg):
        self.lidar_status = msg.data
        self.last_lidar = time.monotonic()

    def on_open_side(self, msg):
        self.open_side = msg.data

    def on_front_distance(self, msg):
        self.front_distance = msg.data
        self.last_front_distance = time.monotonic()#otomatik için

    def on_imu(self, msg):
        self.imu_status = msg.data
        self.last_imu = time.monotonic()

    def on_camera_status(self, msg):
        self.camera_status = msg.data
        self.last_camera = time.monotonic()

    def on_hazard(self, msg):
        self.hazard_detected = msg.data

    def on_contact(self, msg):
        if msg.contacts:
            self.contact_triggered = True

    @staticmethod
    def is_fresh(timestamp, now, timeout):
        return timestamp is not None and now - timestamp <= timeout

    def decide_state(self):
        now = time.monotonic()

        # Physical contact is latched until the FSM is restarted.
        if self.contact_triggered:
            return 'RECOVER'
        ##If dangerous platform is detected it will be hazard stop even if camera data changes
        if self.hazard_latched:
            return 'HAZARD_STOP'

        if (
            self.last_lidar is None
            or self.last_imu is None
            or self.last_camera is None
        ):
            return 'WAIT_SENSORS'

        if not self.is_fresh(self.last_lidar, now, 2.5):
            return 'SAFE_STOP'

        if not self.is_fresh(self.last_imu, now, 2.5):
            return 'SAFE_STOP'

        if not self.is_fresh(self.last_camera, now, 3.0):
            return 'SAFE_STOP'

        if self.imu_status != 'NORMAL':
            return 'SAFE_STOP'

        if self.camera_status in ('WAITING', 'STALE'):
            return 'SAFE_STOP'

        if self.lidar_status not in ('CLEAR', 'WARNING', 'DANGER'):
            return 'SAFE_STOP'

        if (
            self.camera_status == 'DETECTED'
            and self.hazard_detected
        ):
            self.hazard_latched = True
            return 'HAZARD_STOP'

        if self.lidar_status == 'DANGER':
            return 'AVOID'

        if self.lidar_status == 'WARNING':
            return 'CAUTION'

        return 'EXPLORE'

    def control_loop(self):
        new_state = self.decide_state()

        if new_state != self.state:
            event = f'{self.state} -> {new_state}'
            #self.get_logger().info(event)
            #self.event_pub.publish(String(data=event))
            #self.state = new_state
            if new_state == 'SAFE_STOP':
                now = time.monotonic()

                lidar_age = now - self.last_lidar
                imu_age = now - self.last_imu
                camera_age = now - self.last_camera

                event += (
                    f' | lidar={self.lidar_status}'
                    f' ({lidar_age:.2f}s)'
                    f' | imu={self.imu_status}'
                    f' ({imu_age:.2f}s)'
                    f' | camera={self.camera_status}'
                    f' ({camera_age:.2f}s)'
                )

            self.get_logger().info(event)
            self.event_pub.publish(String(data=event))
            self.state = new_state


        self.state_pub.publish(String(data=self.state))

        bumper_status = (
            'CONTACT' if self.contact_triggered else 'CLEAR'
        )

        self.bumper_pub.publish(
            String(data=bumper_status)
        )
        self.bumper_value_pub.publish(
            Float32(data=1.0 if self.contact_triggered else 0.0)
        )

        # Phase 1: keep the robot stopped in every state.
        # Autonomous motion will be enabled after validation.
        #self.cmd_pub.publish(Twist())##otomatik hareket yokken

        # Phase 2: controlled low-speed motion test.
        # Motion remains disabled by default.
        cmd = Twist()
        now = time.monotonic()
        front_is_safe = (
            self.front_distance is not None
            and 1.5 < self.front_distance < 100.0
            and self.is_fresh(
                self.last_front_distance, now, 1.0
            )
        )

        if (
            self.get_parameter('motion_enabled').value
            and self.state == 'EXPLORE'
            and self.camera_status == 'SEARCHING'
            and front_is_safe
        ):
            cmd.linear.x = 0.04

        # All other states publish zero velocity.
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
