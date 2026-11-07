#!/usr/bin/env python3
"""Automated tests for FireScout camera detection."""

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np


# Load the actual camera monitor implementation.
CAMERA_FILE = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "camera_monitor.py"
)

spec = importlib.util.spec_from_file_location(
    "camera_monitor_under_test", CAMERA_FILE
)
camera_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera_module)

CameraMonitor = camera_module.CameraMonitor


class FakePublisher:
    def __init__(self):
        self.messages = []

    def publish(self, msg):
        self.messages.append(msg)


class FakeBridge:
    def imgmsg_to_cv2(self, msg, desired_encoding="bgr8"):
        return msg.frame.copy()

    def cv2_to_imgmsg(self, frame, encoding="bgr8"):
        return SimpleNamespace(
            frame=frame.copy(),
            header=None
        )


class TestCameraMonitor(unittest.TestCase):

    def setUp(self):
        # Run the real processing methods without starting ROS.
        self.node = SimpleNamespace(
            bridge=FakeBridge(),
            last_frame_time=None,
            min_red_area=250.0,
            hazard_pub=FakePublisher(),
            ratio_pub=FakePublisher(),
            status_pub=FakePublisher(),
            debug_pub=FakePublisher()
        )

    def process(self, frame):
        msg = SimpleNamespace(
            frame=frame,
            header=SimpleNamespace(frame_id="camera_link")
        )
        CameraMonitor.process_image(self.node, msg)

    def blank_image(self):
        return np.full(
            (480, 640, 3), 120, dtype=np.uint8
        )

    def test_no_red_object(self):
        frame = self.blank_image()
        self.process(frame)

        self.assertFalse(
            self.node.hazard_pub.messages[-1].data
        )
        self.assertEqual(
            self.node.status_pub.messages[-1].data,
            "SEARCHING"
        )
        self.assertEqual(
            self.node.ratio_pub.messages[-1].data,
            0.0
        )

    def test_large_red_panel(self):
        frame = self.blank_image()

        cv2.rectangle(
            frame,
            (180, 140),
            (270, 250),
            (0, 0, 255),
            -1
        )

        self.process(frame)

        self.assertTrue(
            self.node.hazard_pub.messages[-1].data
        )
        self.assertEqual(
            self.node.status_pub.messages[-1].data,
            "DETECTED"
        )
        self.assertGreater(
            self.node.ratio_pub.messages[-1].data,
            0.02
        )

        debug_image = self.node.debug_pub.messages[-1]
        self.assertEqual(
            debug_image.header.frame_id,
            "camera_link"
        )

        # Bounding box should contain green pixels.
        green_pixels = np.all(
            debug_image.frame == [0, 255, 0],
            axis=2
        )
        self.assertTrue(np.any(green_pixels))

    def test_blue_object_not_detected(self):
        frame = self.blank_image()

        cv2.rectangle(
            frame,
            (180, 140),
            (270, 250),
            (255, 0, 0),
            -1
        )

        self.process(frame)

        self.assertFalse(
            self.node.hazard_pub.messages[-1].data
        )
        self.assertEqual(
            self.node.status_pub.messages[-1].data,
            "SEARCHING"
        )

    def test_small_red_object_not_detected(self):
        frame = self.blank_image()

        cv2.rectangle(
            frame,
            (100, 100),
            (110, 110),
            (0, 0, 255),
            -1
        )

        self.process(frame)

        self.assertFalse(
            self.node.hazard_pub.messages[-1].data
        )
        self.assertGreater(
            self.node.ratio_pub.messages[-1].data,
            0.0
        )

    def test_camera_waiting(self):
        CameraMonitor.check_camera(self.node)

        self.assertEqual(
            self.node.status_pub.messages[-1].data,
            "WAITING"
        )
        self.assertFalse(
            self.node.hazard_pub.messages[-1].data
        )

    def test_camera_stale(self):
        self.node.last_frame_time = 5.0

        with patch.object(
            camera_module.time,
            "monotonic",
            return_value=10.0
        ):
            CameraMonitor.check_camera(self.node)

        self.assertEqual(
            self.node.status_pub.messages[-1].data,
            "STALE"
        )
        self.assertFalse(
            self.node.hazard_pub.messages[-1].data
        )

    def test_recent_camera_frame(self):
        self.node.last_frame_time = 9.0

        with patch.object(
            camera_module.time,
            "monotonic",
            return_value=10.0
        ):
            CameraMonitor.check_camera(self.node)

        self.assertEqual(
            len(self.node.status_pub.messages),
            0
        )


if __name__ == "__main__":
    unittest.main()
