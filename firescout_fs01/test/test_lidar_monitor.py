"""LiDAR sector and status tests without starting ROS or a simulator."""

import importlib.util
import math
from pathlib import Path
import unittest

from sensor_msgs.msg import LaserScan


spec = importlib.util.spec_from_file_location(
    'lidar_monitor', Path(__file__).parents[1] / 'scripts' / 'lidar_monitor.py'
)
lidar_monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lidar_monitor)


def make_scan(default=math.inf, overrides=None):
    """360 beams, one per degree, same layout as the FireScout gpu_lidar."""
    msg = LaserScan()
    msg.angle_min = -math.pi
    msg.angle_max = math.pi
    msg.angle_increment = 2 * math.pi / 360
    msg.range_min = 0.10
    msg.range_max = 8.0
    ranges = [default] * 360
    for degree, distance in (overrides or {}).items():
        ranges[degree + 180] = distance  # beam i points at (i - 180) degrees
    msg.ranges = ranges
    return msg


def sector(msg, name):
    return lidar_monitor.sector_distance(msg, *lidar_monitor.SECTORS[name])


class SectorDistanceTest(unittest.TestCase):
    def test_nearest_obstacle_in_each_sector(self):
        msg = make_scan(overrides={0: 2.5, 10: 1.4, 90: 0.8, -90: 3.0})
        self.assertAlmostEqual(sector(msg, 'front'), 1.4, places=5)
        self.assertAlmostEqual(sector(msg, 'left'), 0.8, places=5)
        self.assertAlmostEqual(sector(msg, 'right'), 3.0, places=5)

    def test_obstacle_outside_sector_is_ignored(self):
        # 45 deg is between the front (+-20) and left (60..120) sectors.
        msg = make_scan(overrides={45: 0.3})
        self.assertEqual(sector(msg, 'front'), math.inf)
        self.assertEqual(sector(msg, 'left'), math.inf)

    def test_all_inf_means_open_space(self):
        self.assertEqual(sector(make_scan(), 'front'), math.inf)

    def test_nan_and_too_close_readings_are_not_measurements(self):
        msg = make_scan(default=math.nan, overrides={5: 0.05})
        self.assertIsNone(sector(msg, 'front'))

    def test_valid_reading_wins_over_inf_and_nan(self):
        msg = make_scan(overrides={-5: math.nan, 5: 1.1})
        self.assertAlmostEqual(sector(msg, 'front'), 1.1, places=5)

    def test_empty_scan_has_no_data(self):
        msg = make_scan()
        msg.ranges = []
        self.assertIsNone(sector(msg, 'front'))

    def test_angles_wrap_around_180(self):
        msg = make_scan()
        self.assertAlmostEqual(lidar_monitor.beam_angle_deg(msg, 0), -180.0, places=5)
        self.assertAlmostEqual(lidar_monitor.beam_angle_deg(msg, 180), 0.0, places=5)
        self.assertAlmostEqual(lidar_monitor.beam_angle_deg(msg, 270), 90.0, places=5)


class StatusTest(unittest.TestCase):
    def test_thresholds(self):
        status = lidar_monitor.obstacle_status
        self.assertEqual(status(0.5, 0.7, 1.2), 'DANGER')
        self.assertEqual(status(0.9, 0.7, 1.2), 'WARNING')
        self.assertEqual(status(1.2, 0.7, 1.2), 'CLEAR')
        self.assertEqual(status(math.inf, 0.7, 1.2), 'CLEAR')
        self.assertEqual(status(None, 0.7, 1.2), 'NO_DATA')

    def test_more_open_side(self):
        side = lidar_monitor.more_open_side
        self.assertEqual(side(2.0, 0.5), 'LEFT')
        self.assertEqual(side(0.5, 2.0), 'RIGHT')
        self.assertEqual(side(math.inf, 3.0), 'LEFT')
        self.assertEqual(side(None, 0.3), 'RIGHT')


if __name__ == '__main__':
    unittest.main()
