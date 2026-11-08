"""Offline ramp geometry checks; these are not Gazebo driving tests."""

import math
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


WORLD = Path(__file__).parents[1] / 'worlds/industrial_world.sdf'


def numbers(element, path):
    return tuple(map(float, element.findtext(path).split()))


def top_edges(collision):
    _, y, z, roll, _, _ = numbers(collision, 'pose')
    _, length, thickness = numbers(collision, 'geometry/box/size')
    y -= thickness / 2 * math.sin(roll)
    z += thickness / 2 * math.cos(roll)
    dy, dz = length / 2 * math.cos(roll), length / 2 * math.sin(roll)
    return (y - dy, z - dz), (y + dy, z + dz)


def ray_hits(origin, direction, model_pose, collision):
    """Slab intersection in the local coordinates of a roll-rotated box."""
    mx, my, mz, _, _, _ = model_pose
    x, y, z, roll, _, _ = numbers(collision, 'pose')
    ox, oy, oz = (origin[i] - (mx + x, my + y, mz + z)[i] for i in range(3))
    dx, dy, dz = direction
    c, s = math.cos(roll), math.sin(roll)
    local_o = (ox, c * oy + s * oz, -s * oy + c * oz)
    local_d = (dx, c * dy + s * dz, -s * dy + c * dz)
    low, high = 0.0, 8.0
    for o, d, size in zip(local_o, local_d, numbers(collision, 'geometry/box/size')):
        if abs(d) < 1e-12:
            if abs(o) > size / 2:
                return False
            continue
        a, b = sorted(((-size / 2 - o) / d, (size / 2 - o) / d))
        low, high = max(low, a), min(high, b)
        if low > high:
            return False
    return True


class DemoRampGeometryTest(unittest.TestCase):
    def setUp(self):
        self.model = ET.parse(WORLD).getroot().find("world/model[@name='imu_demo_ramp']")
        self.assertIsNotNone(self.model)
        self.pose = numbers(self.model, 'pose')
        self.collisions = self.model.findall('link/collision')

    def test_static_real_collision_matches_visible_surface(self):
        self.assertEqual(self.model.findtext('static'), 'true')
        visuals = {v.get('name'): v for v in self.model.findall('link/visual')}
        self.assertEqual(len(self.collisions), 8)
        for collision in self.collisions:
            visual = visuals[collision.get('name') + '_visual']
            self.assertEqual(numbers(collision, 'pose'), numbers(visual, 'pose'))
            self.assertEqual(numbers(collision, 'geometry/box/size'),
                             numbers(visual, 'geometry/box/size'))
            self.assertGreater(float(collision.findtext('surface/friction/ode/mu')), math.tan(math.radians(20)))

    def test_zero_height_toe_continuous_surfaces_and_gentle_angle_changes(self):
        previous = (0.0, 0.0)
        angle = 0.0
        for collision in self.collisions:
            start, end = top_edges(collision)
            self.assertAlmostEqual(start[0], previous[0], places=8)
            self.assertAlmostEqual(start[1], previous[1], places=8)
            current_angle = math.degrees(numbers(collision, 'pose')[3])
            self.assertLessEqual(abs(current_angle - angle), 5.000001)
            self.assertGreaterEqual(end[1] + 1e-8, start[1])
            previous, angle = end, current_angle
        self.assertAlmostEqual(previous[0], 2.5, places=8)
        self.assertAlmostEqual(previous[1], 0.523499685, places=8)
        self.assertAlmostEqual(angle, 0.0)

    def test_width_and_warning_segment_fit_robot(self):
        urdf = ET.parse(WORLD.parents[1] / 'urdf/firescout.urdf.xacro').getroot()
        props = {p.get('name'): float(p.get('value')) for p in
                 urdf.findall('{http://www.ros.org/wiki/xacro}property')}
        wheel = urdf.find("{http://www.ros.org/wiki/xacro}macro[@name='wheel']")
        wheel_width = float(wheel.find('link/collision/geometry/cylinder').get('length'))
        robot_width = props['wheel_sep'] + wheel_width
        for collision in self.collisions:
            self.assertGreaterEqual(numbers(collision, 'geometry/box/size')[0], robot_width + 0.4)
        slope = next(c for c in self.collisions if c.get('name') == 'slope_20')
        self.assertAlmostEqual(math.degrees(numbers(slope, 'pose')[3]), 20.0, places=8)
        start, end = top_edges(slope)
        self.assertGreaterEqual(end[0] - start[0], 0.9)
        self.assertGreaterEqual(numbers(self.collisions[-1], 'geometry/box/size')[1], 0.6)

    def test_lane_clear_of_spawn_corridor_crates_and_wall(self):
        x, y, _, roll, pitch, yaw = self.pose
        self.assertEqual((roll, pitch, yaw), (0.0, 0.0, 0.0))
        self.assertGreater(x - 0.45, 1.625 + 0.5)  # crate_two's right edge
        self.assertGreater(3.925 - (x + 0.45), 0.5)  # inner right wall
        self.assertGreater(y, -1.8 + 0.5)  # normal +X spawn corridor
        self.assertGreater(2.925 - (y + 2.5), 0.6)  # inner back wall

    def test_spawn_front_scan_is_not_blocked_by_ramp(self):
        # Actual scanner is 0.26 + 0.06 = 0.32 m above the flat floor.
        for quarter_degree in range(-80, 81):
            angle = math.radians(quarter_degree / 4)
            direction = (math.cos(angle), math.sin(angle), 0.0)
            self.assertFalse(any(ray_hits((0.0, -1.8, 0.32), direction, self.pose, c)
                                 for c in self.collisions), quarter_degree / 4)

    def test_existing_red_panel_view_is_not_occluded(self):
        # Conservative horizontal camera FOV (+/-35 deg around +Y).
        for y in (0.8, 1.8):
            for degrees in range(55, 126):
                angle = math.radians(degrees)
                self.assertFalse(any(ray_hits((-2.8, y + 0.255, 0.18),
                                             (math.cos(angle), math.sin(angle), 0.0), self.pose, c)
                                     for c in self.collisions))


if __name__ == '__main__':
    unittest.main()
