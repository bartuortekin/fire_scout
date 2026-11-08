
# FireScout FS-01 — Camera Detection Test Results

## 1. Test Information

- Date: 2026-11-07
- Robot: FireScout FS-01
- Simulation: Gazebo Jetty
- ROS 2: Lyrical
- Environment: Ubuntu 26.04 in VMware
- Sensor: Simulated RGB camera
- Processing: OpenCV HSV-based red-region detection

## 2. Test Objective

Verify that the camera monitor can:

1. Receive simulated camera images through ROS 2.
2. Detect a red hazard marker.
3. Publish detection status and red-pixel ratio.
4. Visualize the detected region in RViz.
5. Handle normal and missing camera data.

The red panel represents a simulated hazard marker,
not an actual fire or smoke detector.

## 3. Experiment A — No Red Target Visible

The robot camera was directed toward an area without
a visible red hazard marker.

Observed ROS 2 outputs:

| Topic | Result |
|---|---|
| /firescout/camera/red_ratio | 0.0 |
| /firescout/camera/hazard_detected | false |
| /firescout/camera/status | SEARCHING |

Result: No red target was detected.

## 4. Experiment B — Red Target Visible

The robot was rotated until the simulated red
hazard marker entered the camera field of view.

Observed ROS 2 outputs:

| Topic | Result |
|---|---|
| /firescout/camera/red_ratio | 0.018460286781191826 |
| /firescout/camera/hazard_detected | true |
| /firescout/camera/status | DETECTED |

The red-pixel ratio corresponds to approximately
1.846% of the image area.

The RViz debug image also showed a green bounding
box around the detected red region.

Result: The target was successfully detected and
the detection was published through ROS 2.

## 5. Visualization

The processed image was visualized in RViz using:

- Topic: /firescout/camera/debug_image
- Message type: sensor_msgs/msg/Image
- Reliability Policy: Best Effort

The initial RViz Image display used Reliable QoS
and showed "No Image". Changing the reliability
policy to Best Effort allowed the images to appear.

## 6. Automated Unit Tests

Command:

    python3 -m unittest discover \
      -s firescout_fs01/test \
      -p "test_camera_monitor.py" -v

Test cases:

1. No red object
2. Large red panel
3. Blue object rejection
4. Small red object rejection
5. Camera WAITING state
6. Camera STALE state
7. Recent camera frame handling

Results:

- Tests executed: 7
- Tests passed: 7
- Tests failed: 0
- Execution time: 0.110 seconds

The detailed output is saved in unit_tests.log.

## 7. Conclusion

The camera monitor successfully received and
processed simulated RGB images, detected a red
hazard marker, and published the results through
ROS 2 topics.

The module is ready to provide detection inputs
to the FireScout behavior node.

Automatic robot behavior based on these camera
outputs has not yet been demonstrated and must
be verified separately during FSM integration.

## 8. Limitations

- Detection relies on red color thresholds.
- Other red objects may cause false positives.
- Results depend on the camera viewing direction.
- The current detector does not require detection
  in multiple consecutive frames.
- Camera STALE status must be handled separately
  by the FSM.
