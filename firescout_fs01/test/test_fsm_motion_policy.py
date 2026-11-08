"""ROS kurulumu olmadan saf hareket kurallarının ve FSM kararının testleri.

Run: python3 -m unittest discover -s firescout_fs01/test -p "test_fsm_*.py" -v
The FSM source is parsed via AST so the test does not need ROS Python modules.
"""
import ast
import math
from pathlib import Path
import types
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts' / 'firescout_fsm.py'
tree = ast.parse(SOURCE.read_text(encoding='utf-8'))

def load_func(name, in_class=False):
    nodes = tree.body
    if in_class:
        nodes = next(node for node in nodes if isinstance(node, ast.ClassDef)
                     and node.name == 'FireScoutFSM').body
    target = next(node for node in nodes if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and node.name == name)
    target = ast.fix_missing_locations(ast.FunctionDef(
        name=target.name, args=target.args, body=target.body, decorator_list=[],
        returns=target.returns, type_comment=None))
    code = compile(ast.Module(body=[target], type_ignores=[]), str(SOURCE), 'exec')
    namespace = {'math': math}
    exec(code, namespace)
    return namespace[name]

motion_policy = load_func('motion_policy')
decide_state = load_func('decide_state', True)
is_fresh = load_func('is_fresh', True)
choose_turn_side = load_func('choose_turn_side', True)

class MotionPolicyTests(unittest.TestCase):
    def test_disabled(self):
        self.assertEqual(motion_policy('EXPLORE', False, 'SEARCHING', 3.0, True), (0.0, 0.0))

    def test_explore_forward(self):
        self.assertEqual(motion_policy('EXPLORE', True, 'SEARCHING', 3.0, True), (0.04, 0.0))

    def test_explore_cannot_advance_near_wall(self):
        self.assertEqual(motion_policy('EXPLORE', True, 'SEARCHING', 1.1, True), (0.0, 0.0))

    def test_caution_slow(self):
        self.assertEqual(motion_policy('CAUTION', True, 'SEARCHING', 0.83, True), (0.02, 0.0))

    def test_caution_too_close_stops(self):
        self.assertEqual(motion_policy('CAUTION', True, 'SEARCHING', 0.75, True), (0.0, 0.0))

    def test_turn_right(self):
        self.assertEqual(motion_policy('AVOID', True, 'SEARCHING', 0.5, True, -1, 2.0, True), (0.0, -0.25))

    def test_turn_left(self):
        self.assertEqual(motion_policy('AVOID', True, 'SEARCHING', 0.5, True, +1, 2.0, True), (0.0, +0.25))

    def test_turn_requires_measured_clear_side(self):
        self.assertEqual(motion_policy('AVOID', True, 'SEARCHING', 0.5, True, -1, 0.5, True), (0.0, 0.0))
        self.assertEqual(motion_policy('AVOID', True, 'SEARCHING', 0.5, True, -1, 2.0, False), (0.0, 0.0))

    def test_turn_too_close_stops(self):
        self.assertEqual(motion_policy('AVOID', True, 'SEARCHING', 0.25, True, +1, 2.0, True), (0.0, 0.0))

    def test_stale_or_camera_not_searching_stops(self):
        self.assertEqual(motion_policy('EXPLORE', True, 'STALE', 4.0, True), (0.0, 0.0))
        self.assertEqual(motion_policy('EXPLORE', True, 'SEARCHING', 4.0, False), (0.0, 0.0))
        self.assertEqual(motion_policy('AVOID', True, 'DETECTED', 0.5, True, -1, 2.0, True), (0.0, 0.0))

    def test_safety_states_stop(self):
        for state in ('WAIT_SENSORS', 'SAFE_STOP', 'RECOVER', 'HAZARD_STOP'):
            with self.subTest(state=state):
                self.assertEqual(motion_policy(state, True, 'SEARCHING', 3.0, True), (0.0, 0.0))

    def test_nan_or_infinite_front_stops(self):
        for distance in (math.nan, math.inf, -1.0):
            self.assertEqual(motion_policy('EXPLORE', True, 'SEARCHING', distance, True), (0.0, 0.0))

class StateDecisionTests(unittest.TestCase):
    def setup_node(self):
        now = 100.0
        node = types.SimpleNamespace(
            state='EXPLORE', lidar_status='CLEAR', imu_status='NORMAL', camera_status='SEARCHING',
            front_distance=3.0, hazard_detected=False, hazard_latched=False,
            contact_triggered=False, avoid_fault_latched=False,
            last_lidar=now, last_imu=now, last_camera=now, last_front_distance=now,
            last_hazard=now, avoid_started=None, avoid_clearance_m=1.35,
            last_open_side=now, open_side='RIGHT', last_right_distance=now, right_distance=2.0,
            last_left_distance=now, left_distance=1.0,
            is_fresh=lambda timestamp, t, threshold: is_fresh(timestamp, t, threshold))
        return node, now

    def test_clear_and_warning(self):
        node, now = self.setup_node()
        self.assertEqual(decide_state(node, now), 'EXPLORE')
        node.lidar_status, node.front_distance = 'WARNING', 0.85
        self.assertEqual(decide_state(node, now), 'CAUTION')

    def test_danger_and_avoid_hysteresis(self):
        node, now = self.setup_node()
        node.lidar_status, node.front_distance = 'DANGER', 0.50
        self.assertEqual(decide_state(node, now), 'AVOID')
        node.state, node.lidar_status, node.front_distance, node.avoid_started = 'AVOID', 'CLEAR', 1.25, 99.0
        self.assertEqual(decide_state(node, now), 'AVOID')
        node.front_distance = 1.35
        self.assertEqual(decide_state(node, now), 'AVOID')
        node.front_distance = 1.3501
        self.assertEqual(decide_state(node, now), 'CAUTION')
        node.front_distance = 1.5
        self.assertEqual(decide_state(node, now), 'CAUTION')
        node.front_distance = 1.5001
        self.assertEqual(decide_state(node, now), 'EXPLORE')

    def test_camera_hazard_is_latched(self):
        node, now = self.setup_node()
        node.camera_status, node.hazard_detected = 'DETECTED', True
        self.assertEqual(decide_state(node, now), 'HAZARD_STOP')
        self.assertTrue(node.hazard_latched)
        node.camera_status, node.hazard_detected = 'SEARCHING', False
        self.assertEqual(decide_state(node, now), 'HAZARD_STOP')

    def test_contact_prioritized(self):
        node, now = self.setup_node()
        node.hazard_latched, node.contact_triggered = True, True
        self.assertEqual(decide_state(node, now), 'RECOVER')

    def test_stale_sensor_safe_stop(self):
        node, now = self.setup_node()
        node.last_front_distance = 98.0
        self.assertEqual(decide_state(node, now), 'SAFE_STOP')
        node.last_front_distance = now
        node.camera_status = 'STALE'
        self.assertEqual(decide_state(node, now), 'SAFE_STOP')

    def test_missing_sensor_waits(self):
        node, now = self.setup_node()
        node.last_camera = None
        self.assertEqual(decide_state(node, now), 'WAIT_SENSORS')

    def test_choose_turn_side_checks_freshness(self):
        node, now = self.setup_node()
        self.assertEqual(choose_turn_side(node, now), -1)
        node.last_right_distance = 98.0
        self.assertEqual(choose_turn_side(node, now), 0)
        node.open_side='LEFT'
        self.assertEqual(choose_turn_side(node, now), 1)

if __name__ == '__main__':
    unittest.main(verbosity=2)
