
# FireScout FS-01 — Camera Monitor

## 1. Objective

The camera monitor provides visual hazard-marker detection for
the FireScout FS-01 robot.

It processes simulated RGB camera images using OpenCV,
detects red regions, and publishes the detection results
through ROS 2 topics.

The red panel represents a simulated hazard marker.
This module does not detect actual fire or smoke.

## 2. Camera Input

| Topic | Message Type |
|---|---|
| /camera/image_raw | sensor_msgs/msg/Image |

The camera is mounted on the FireScout robot and simulated
in Gazebo Jetty.

## 3. Detection Algorithm

The processing pipeline consists of:

1. Subscribe to the RGB camera image.
2. Convert the ROS Image message to OpenCV BGR format
   using cv_bridge.
3. Convert the image from BGR to HSV.
4. Create two HSV masks for red colors:
   - H: 0–10, S: 100–255, V: 80–255
   - H: 170–179, S: 100–255, V: 80–255
5. Combine the masks.
6. Apply morphological opening using a 5×5 kernel
   to reduce small noise.
7. Find external contours.
8. Select the largest red contour.
9. Report a detection when its area is at least 250 px².
10. Draw a green bounding box around the detected region.
11. Publish detection results and the annotated image.

The detection threshold is configurable through the
ROS 2 parameter `min_red_area`.

## 4. ROS 2 Outputs

| Topic | Message Type | Description |
|---|---|---|
| /firescout/camera/hazard_detected | std_msgs/msg/Bool | Red target detection result |
| /firescout/camera/red_ratio | std_msgs/msg/Float32 | Ratio of red pixels to total image pixels |
| /firescout/camera/status | std_msgs/msg/String | Camera processing state |
| /firescout/camera/debug_image | sensor_msgs/msg/Image | Annotated camera image |

Possible camera states:

- WAITING: No image has been received yet.
- SEARCHING: Images are received, but no qualifying red region is detected.
- DETECTED: A qualifying red region is detected.
- STALE: No new image has arrived for more than 2 seconds.

## 5. Running the Camera Monitor

Source ROS 2 and the workspace containing the package:

```bash
source /opt/ros/lyrical/setup.bash
source <workspace>/install/setup.bash
```

Start the FireScout simulation:

```bash
ros2 launch firescout_fs01 simulation.launch.py sim_mode:=vm
```

In another terminal, start the camera monitor:

```bash
ros2 run firescout_fs01 camera_monitor.py
```

For a native graphics environment, the simulation also
supports `sim_mode:=native`.

## 6. RViz Visualization

Add an Image display with these settings:

- Topic: /firescout/camera/debug_image
- Reliability Policy: Best Effort
- Durability Policy: Volatile

When a target is detected, the processed image shows
a green bounding box and the text DETECTED.

## 7. Automated Tests

Run the tests from the repository root:

```bash
source /opt/ros/lyrical/setup.bash
python3 -m unittest discover \
  -s firescout_fs01/test \
  -p "test_camera_monitor.py" -v
```

Seven tests cover:

- No red target
- Large red target
- Blue object rejection
- Small red region rejection
- WAITING state
- STALE state
- Recent frame handling

## 8. FSM Integration

A future behavior node can subscribe to:

- /firescout/camera/hazard_detected
- /firescout/camera/status

When the camera reports DETECTED, the robot may enter
an inspection or alert state.

The FSM must distinguish between SEARCHING, WAITING,
and STALE states. A false hazard_detected value during
a camera timeout does not establish that the area is safe.

## 9. Limitations

- Detection is based on red color, not semantic recognition.
- Other sufficiently large red objects may produce false positives.
- Results depend on camera visibility and lighting.
- The current algorithm has no temporal confirmation.
- A successful detection does not independently control the robot.
  The behavior node must implement motion decisions.
