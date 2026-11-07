#!/usr/bin/env python3

import time

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32, String


class CameraMonitor(Node):

    def __init__(self):
        super().__init__('camera_monitor')

        self.bridge = CvBridge()
        self.last_frame_time = None

        self.declare_parameter('min_red_area', 250.0)
        self.min_red_area = self.get_parameter(
            'min_red_area'
        ).value

        self.image_sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.process_image,
            qos_profile_sensor_data
        )

        self.hazard_pub = self.create_publisher(
            Bool,
            '/firescout/camera/hazard_detected',
            10
        )

        self.ratio_pub = self.create_publisher(
            Float32,
            '/firescout/camera/red_ratio',
            10
        )

        self.status_pub = self.create_publisher(
            String,
            '/firescout/camera/status',
            10
        )

        self.debug_pub = self.create_publisher(
            Image,
            '/firescout/camera/debug_image',
            qos_profile_sensor_data
        )

        self.timer = self.create_timer(
            0.5, self.check_camera
        )

        self.get_logger().info(
            'Camera Monitor started.'
        )

    def process_image(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(
                msg, desired_encoding='bgr8'
            )
        except Exception as exc:
            self.get_logger().error(str(exc))
            return

        self.last_frame_time = time.monotonic()

        hsv = cv2.cvtColor(
            frame, cv2.COLOR_BGR2HSV
        )

        # Red occupies two ranges in OpenCV HSV.
        mask1 = cv2.inRange(
            hsv, (0, 100, 80), (10, 255, 255)
        )
        mask2 = cv2.inRange(
            hsv, (170, 100, 80), (179, 255, 255)
        )

        mask = cv2.bitwise_or(mask1, mask2)

        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (5, 5)
        )

        mask = cv2.morphologyEx(
            mask, cv2.MORPH_OPEN, kernel
        )

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        red_pixels = cv2.countNonZero(mask)
        total_pixels = frame.shape[0] * frame.shape[1]
        red_ratio = red_pixels / total_pixels

        detected = False

        if contours:
            largest = max(
                contours, key=cv2.contourArea
            )
            area = cv2.contourArea(largest)

            if area >= self.min_red_area:
                detected = True

                x, y, w, h = cv2.boundingRect(
                    largest
                )

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )

        status = (
            'DETECTED' if detected else 'SEARCHING'
        )

        cv2.putText(
            frame,
            status,
            (15, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0) if detected
            else (255, 255, 255),
            2
        )

        self.hazard_pub.publish(
            Bool(data=detected)
        )
        self.ratio_pub.publish(
            Float32(data=float(red_ratio))
        )
        self.status_pub.publish(
            String(data=status)
        )

        debug_msg = self.bridge.cv2_to_imgmsg(
            frame, encoding='bgr8'
        )
        debug_msg.header = msg.header
        self.debug_pub.publish(debug_msg)

    def check_camera(self):
        if self.last_frame_time is None:
            status = 'WAITING'
        elif time.monotonic() - self.last_frame_time > 2.0:
            status = 'STALE'
        else:
            return

        self.status_pub.publish(
            String(data=status)
        )
        self.hazard_pub.publish(
            Bool(data=False)
        )


def main(args=None):
    rclpy.init(args=args)
    node = CameraMonitor()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
