"""Geometry constraints for the low demo lane; not a driving test."""
import math
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).parents[1]


class RoughGroundGeometryTests(unittest.TestCase):
    def setUp(self):
        self.world = ET.parse(ROOT / 'worlds/industrial_world.sdf').getroot().find('world')
        self.bumps = [m for m in self.world.findall('model')
                      if m.get('name').startswith('rough_ground_bump_')]

    def test_real_surface_is_wide_low_continuous_and_below_warning_slope(self):
        self.assertIn(len(self.bumps), (1, 5))
        robot = ET.parse(ROOT / 'urdf/firescout.urdf.xacro').getroot()
        props = {p.get('name'): float(p.get('value')) for p in
                 robot.findall('{http://www.ros.org/wiki/xacro}property')}
        base = robot.find("link[@name='base_link']/collision")
        center_z = float(base.find('origin').get('xyz').split()[2])
        body_height = float(base.find('geometry/box').get('size').split()[2])
        clearance = center_z - body_height/2
        for bump in self.bumps:
            self.assertEqual(bump.findtext('static'), 'true')
            previous, angles, heights = (0., 0.), [], []
            visuals = {v.get('name'): v for v in bump.findall('link/visual')}
            for col in bump.findall('link/collision'):
                vis = visuals[col.get('name') + '_visual']
                self.assertEqual(col.findtext('pose'), vis.findtext('pose'))
                self.assertEqual(col.findtext('geometry/box/size'), vis.findtext('geometry/box/size'))
                x, _, z, _, pitch, _ = map(float, col.findtext('pose').split())
                length, width, thickness = map(float, col.findtext('geometry/box/size').split())
                top_x = x + thickness/2 * math.sin(pitch)
                top_z = z + thickness/2 * math.cos(pitch)
                dx, dz = length/2 * math.cos(pitch), -length/2 * math.sin(pitch)
                begin, end = (top_x-dx, top_z-dz), (top_x+dx, top_z+dz)
                for actual, expected in zip(begin, previous):
                    self.assertAlmostEqual(actual, expected, places=9)
                previous = end
                angles.append(pitch)
                heights.extend((begin[1], end[1]))
                self.assertGreater(width, props['wheel_sep'] + .035 + .4)
            self.assertAlmostEqual(previous[0], .6, places=9)
            self.assertAlmostEqual(previous[1], 0, places=9)
            self.assertLessEqual(max(heights), .020000001)
            self.assertLess(max(heights), props['wheel_r']/3)
            self.assertLess(max(heights), clearance/3)
            self.assertLess(max(abs(a) for a in angles), math.radians(7))
            self.assertLess(abs(angles[0]), math.radians(1))
            self.assertLess(abs(angles[-1]), math.radians(1))
            self.assertLess(max(abs(b-a) for a,b in zip(angles, angles[1:])), math.radians(3.2))

    def test_lane_preserves_ramp_spawn_corridor_and_obstacles(self):
        self.assertIsNotNone(self.world.find("model[@name='imu_demo_ramp']"))
        starts = []
        for bump in self.bumps:
            x,y,z,r,p,yaw = map(float, bump.findtext('pose').split())
            self.assertEqual((y,z,r,p,yaw), (-.9,0,0,0,0))
            self.assertGreater(y-.4, -1.8+.3)
            self.assertLess(y+.4, -.05-.3)  # crate_one near edge
            self.assertLess(x+.6, 2.45-.3)  # ramp near edge
            self.assertGreater(x, -3.925+.8)
            starts.append(x)
        for a,b in zip(sorted(starts),sorted(starts)[1:]):
            self.assertGreaterEqual(b-a-.6, .399999999)


if __name__ == '__main__':
    unittest.main()
