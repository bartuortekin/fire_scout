#!/usr/bin/env python3
"""Place the real Gazebo robot on a ramp; record native IMU and monitor outputs.

Uses an existing industrial_world session. Never publishes IMU or cmd_vel.
The robot must initially be parked at (0, -1.8) with yaw 0, as in the launch file.
"""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import signal
import subprocess
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from rosidl_runtime_py.convert import message_to_ordereddict
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32, String


ROOT = Path(__file__).resolve().parents[1]
WORLD = '/world/industrial_world'
TOPICS = ['/imu/data', '/firescout/imu/roll_deg',
          '/firescout/imu/pitch_deg', '/firescout/imu/tilt_status', '/clock']


def run_test(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)  # Never overwrite earlier evidence.
    (out / 'screenshots').mkdir()
    rviz_before = (ROOT / 'firescout_fs01/rviz/firescout.rviz').read_bytes()
    rclpy.init()
    node = rclpy.create_node('imu_physical_evidence')
    start = time.monotonic()
    phase = 'startup'
    records = []
    phases = []
    children = []
    log_files = []
    ramp_created = False
    robot_moved = False
    trace = (out / 'samples.jsonl').open('w')
    commands = (out / 'commands.jsonl').open('w')

    def record(topic, msg):
        row = dict(t=time.monotonic() - start, phase=phase, topic=topic,
                   data=message_to_ordereddict(msg))
        trace.write(json.dumps(row) + '\n')
        records.append(row)

    subscriptions = [node.create_subscription(
        kind, topic, lambda msg, topic=topic: record(topic, msg), qos
    ) for topic, kind, qos in (
        (TOPICS[0], Imu, qos_profile_sensor_data),
        (TOPICS[1], Float32, 10), (TOPICS[2], Float32, 10), (TOPICS[3], String, 10))]

    def pump(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.02)

    def command(argv):
        result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
        commands.write(json.dumps(dict(t=time.monotonic() - start, argv=argv,
                                       returncode=result.returncode, stdout=result.stdout,
                                       stderr=result.stderr)) + '\n')
        commands.flush()
        if result.returncode:
            raise RuntimeError(f'Command failed: {argv}\n{result.stderr}')
        return result.stdout

    def service(name, reqtype, request):
        reply = command(['gz', 'service', '-s', WORLD + name, '--reqtype', reqtype,
                         '--reptype', 'gz.msgs.Boolean', '--timeout', '5000', '--req', request])
        if 'data: true' not in reply:
            raise RuntimeError(f'{name}: {reply}')

    def place(x, z, pitch):
        service('/set_pose/blocking', 'gz.msgs.Pose',
                f'name: "firescout_fs01" position {{x: {x} y: -1.8 z: {z}}} '
                f'orientation {{x: 0 y: {math.sin(pitch / 2)} z: 0 w: {math.cos(pitch / 2)}}}')

    def spawn(argv, filename):
        logfile = (out / filename).open('w')
        log_files.append(logfile)
        process = subprocess.Popen(argv, stdout=logfile, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        children.append(process)
        return process

    def sample(label, expected):
        nonlocal phase
        phase = label + '_settle'
        print(f'{label}: settling for {args.settle_seconds}s...', flush=True)
        pump(args.settle_seconds)
        phase = label
        phases.append(dict(name=label, start=time.monotonic() - start))
        print(f'{label}: recording {args.sample_seconds}s; expected {expected}. '
              'Take a screenshot now.', flush=True)
        pump(args.sample_seconds)
        phases[-1]['end'] = time.monotonic() - start
        pose = command(['gz', 'model', '-m', 'firescout_fs01', '-p'])
        (out / f'{label}_model_pose.txt').write_text(pose)

    try:
        pump(3)
        publishers = node.get_publishers_info_by_topic('/imu/data')
        if len(publishers) != 1 or publishers[0].node_name != 'ros_gz_bridge':
            raise RuntimeError('/imu/data must have exactly one publisher: ros_gz_bridge.')
        (out / 'imu_source.txt').write_text(command(['ros2', 'topic', 'info', '/imu/data', '--verbose']))
        (out / 'initial_model_pose.txt').write_text(command(['gz', 'model', '-m', 'firescout_fs01', '-p']))
        # Guard the documented restore position before moving anything.
        initial = (out / 'initial_model_pose.txt').read_text()
        xyz_rpy = re.findall(r'\[\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*\]', initial)
        if len(xyz_rpy) < 2:
            raise RuntimeError('Could not read initial model pose.')
        xyz, rpy = ([float(v) for v in values] for values in xyz_rpy[-2:])
        if max(abs(xyz[0]), abs(xyz[1] + 1.8), abs(xyz[2]), *(abs(v) for v in rpy)) > 0.02:
            raise RuntimeError('Robot is not at the documented initial parking pose; no movement done.')
        if 'imu_monitor' not in node.get_node_names():
            spawn(['ros2', 'run', 'firescout_fs01', 'imu_monitor.py'], 'imu_monitor.log')
        spawn(['ros2', 'bag', 'record', '--disable-keyboard-controls', '-o', str(out / 'bag'),
               '--topics', *TOPICS], 'bag_record.log')
        pump(5)
        sample('01_flat_NORMAL', 'NORMAL')
        phase = 'placing_ramp'
        service('/create/blocking', 'gz.msgs.EntityFactory',
                f'sdf_filename: "{ROOT / "firescout_fs01/test/fixtures/imu_ramp_20deg.sdf"}" '
                'allow_renaming: false')
        ramp_created = True
        robot_moved = True
        place(1.7, 0.55, math.radians(-20))
        sample('02_ramp_WARNING', 'WARNING')
        phase = 'returning_to_floor'
        place(0, 0.03, 0)
        sample('03_flat_NORMAL', 'NORMAL')
    finally:
        phase = 'cleanup'
        try:
            if robot_moved:
                place(0, 0.03, 0)
                pump(3)
            if ramp_created:
                service('/remove/blocking', 'gz.msgs.Entity',
                        'name: "imu_test_ramp_20deg" type: MODEL')
        finally:
            for process in reversed(children):
                if process.poll() is None:
                    process.send_signal(signal.SIGINT)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.wait(timeout=5)
            for logfile in log_files:
                logfile.close()
            trace.close()
            commands.close()
            node.destroy_node()
            rclpy.shutdown()
            assert (ROOT / 'firescout_fs01/rviz/firescout.rviz').read_bytes() == rviz_before

    summary = {'phases': [], 'rviz_sha256': hashlib.sha256(rviz_before).hexdigest()}
    for stage in phases:
        rows = [row for row in records if row['phase'] == stage['name']]
        values = {topic: [row['data']['data'] for row in rows if row['topic'] == topic]
                  for topic in TOPICS[1:4]}
        counts = Counter(row['topic'] for row in rows)
        expected = 'WARNING' if 'ramp' in stage['name'] else 'NORMAL'
        roll, pitch, statuses = (values[topic] for topic in TOPICS[1:4])
        valid_angles = (all(abs(v) < 3 for v in roll) and
                        all(17 < abs(v) < 23 for v in pitch)) if expected == 'WARNING' else (
                            all(abs(v) < 3 for v in roll + pitch))
        passed = (counts['/imu/data'] >= 20 and len(roll) >= 5 and len(pitch) >= 5 and
                  len(statuses) >= 5 and set(statuses) == {expected} and valid_angles)
        summary['phases'].append(dict(**stage, counts=dict(counts), statuses=dict(Counter(statuses)),
                                      roll_range=[min(roll), max(roll)] if roll else None,
                                      pitch_range=[min(pitch), max(pitch)] if pitch else None,
                                      passed=passed))
    summary['passed'] = len(phases) == 3 and all(p['passed'] for p in summary['phases'])
    (out / 'summary.json').write_text(json.dumps(summary, indent=2))
    plot(records, phases, out)
    print(json.dumps(summary, indent=2), flush=True)
    if not summary['passed']:
        raise RuntimeError('Physical test did not pass; keep evidence and inspect summary.')


def plot(records, phases, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, (angles, statuses) = plt.subplots(2, 1, figsize=(11, 6), sharex=True,
                                         gridspec_kw={'height_ratios': [3, 1]})
    for topic, label in ((TOPICS[1], 'roll'), (TOPICS[2], 'pitch')):
        rows = [row for row in records if row['topic'] == topic]
        angles.plot([r['t'] for r in rows], [r['data']['data'] for r in rows], label=label)
    for threshold in (-15, -12, 12, 15):
        angles.axhline(threshold, color='grey', ls='--', lw=0.7)
    mapping = {'UNKNOWN': -1, 'NORMAL': 0, 'WARNING': 1}
    rows = [row for row in records if row['topic'] == TOPICS[3]]
    statuses.step([r['t'] for r in rows], [mapping[r['data']['data']] for r in rows], where='post')
    for stage in phases:
        angles.axvspan(stage['start'], stage['end'], alpha=0.10, color='green')
        angles.text((stage['start'] + stage['end']) / 2, 4, stage['name'], ha='center', fontsize=8)
    statuses.set_yticks([-1, 0, 1], ['UNKNOWN', 'NORMAL', 'WARNING'])
    statuses.set_xlabel('Real elapsed time (s)')
    angles.set_ylabel('Published angle (deg)')
    angles.legend()
    angles.grid(alpha=0.3)
    fig.suptitle('FireScout: native Gazebo IMU, flat -> 20 deg ramp -> flat')
    fig.tight_layout()
    fig.savefig(out / 'angles_and_status.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--settle-seconds', type=float, default=8.0)
    parser.add_argument('--sample-seconds', type=float, default=12.0)
    arguments = parser.parse_args()
    if arguments.settle_seconds < 3 or arguments.sample_seconds < 5:
        parser.error('Use at least 3 s settling and 5 s sampling.')
    run_test(arguments)
