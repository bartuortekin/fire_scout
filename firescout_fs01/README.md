
# FireScout FS-01

ROS 2 Lyrical ve Gazebo Jetty kullanılarak geliştirilen diferansiyel sürüşlü mobil keşif robotu.

## 1. Project Overview

FireScout FS-01, yangın riski taşıyan endüstriyel ortamların keşfi için tasarlanmış bir mobil robot simülasyonudur.

Robot iki tahrikli tekerlek ve bir arka destek tekerine sahiptir.

### Sensors

| Sensor | Purpose | ROS 2 Topic |
|---|---|---|
| LiDAR | Obstacle detection | `/scan` |
| RGB Camera | Visual perception | `/camera/image_raw` |
| IMU | Motion and orientation measurements | `/imu/data` |
| Contact Sensor | Front bumper collision detection | `/bumper/contacts` |

Other topics:
- `/cmd_vel` — Differential-drive velocity commands
- `/joint_states` — Joint states
- `/clock` — Simulation time

## 2. Development Environment

- Ubuntu 26.04
- ROS 2 Lyrical
- Gazebo Jetty
- RViz 2
- Python 3
- URDF / Xacro / SDF
- ros_gz_bridge

## 3. Installation

ROS 2 Lyrical must already be installed.

Install the required packages:

```bash
sudo apt update
sudo apt install ros-lyrical-xacro ros-lyrical-ros-gz \
  ros-lyrical-robot-state-publisher ros-lyrical-rviz2 \
  python3-colcon-common-extensions
```

Copy the `firescout_fs01` folder into a ROS 2 workspace:

```bash
source /opt/ros/lyrical/setup.bash
mkdir -p ~/firescout_ws/src
cp -r firescout_fs01 ~/firescout_ws/src/
cd ~/firescout_ws
colcon build --symlink-install --packages-select firescout_fs01
source install/setup.bash
```

The copy command assumes it is executed from the repository root.

## 4. Launch Instructions

In each new terminal:

```bash
source /opt/ros/lyrical/setup.bash
source ~/firescout_ws/install/setup.bash
```

### VMware

```bash
ros2 launch firescout_fs01 simulation.launch.py sim_mode:=vm
```

Uses:
- Gazebo Server: OGRE2
- Gazebo GUI: OGRE
- Software-rendering environment setting for the server

**Status: Tested successfully on VMware.**

### Native Ubuntu / Dual Boot

```bash
ros2 launch firescout_fs01 simulation.launch.py sim_mode:=native
```

Uses standard Gazebo startup.

**Status: Not yet validated by the team.**

The default mode is `vm`.

## 5. Sensor Verification

List ROS topics:

```bash
ros2 topic list
```

LiDAR:

```bash
ros2 topic hz /scan
ros2 topic echo /scan --once
```

Camera:

```bash
ros2 topic hz /camera/image_raw
```

IMU:

```bash
ros2 topic echo /imu/data --once
```

Contact sensor:

```bash
ros2 topic echo /bumper/contacts
```

The contact topic requires an actual collision to produce contact data.

## 6. Manual Robot Control

Move forward:

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.15}, angular: {z: 0.0}}'
```

Stop the continuous publication with `Ctrl+C`, then send zero velocity:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.0}, angular: {z: 0.0}}'
```

Avoid driving into obstacles during manual testing.

## 7. Verified Results

VMware testing confirmed:

- Gazebo world and FireScout model loaded successfully.
- Robot visualization worked in RViz.
- Four sensor connections were tested.
- LiDAR provided 360 measurements per scan.
- At a stationary test position: 215 valid and 145 INF readings.
- Nearest obstacle measured approximately 1.75 m.
- LiDAR publication rate measured approximately 7.27 Hz.
- Camera images and IMU measurements were received.
- Contact sensor detected a controlled bumper collision.
- Differential-drive motion was verified using `/cmd_vel`.

LiDAR readings and publication rates depend on the scene and system performance.

## 8. Current Limitations

- Autonomous exploration and decision-making are not yet implemented.
- No actual flame or temperature sensor is included.
- The red risk panel is currently visual only.
- Native Ubuntu launch mode has not yet been tested.
- Physics and robot geometry may require further tuning.

## 9. Project Files

- `urdf/firescout.urdf.xacro` — Robot model
- `worlds/industrial_world.sdf` — Gazebo environment
- `config/bridge.yaml` — ROS 2 / Gazebo topic bridges
- `launch/simulation.launch.py` — Simulation launcher
- `rviz/firescout.rviz` — RViz configuration

Previous versions are stored in the repository's `backups/` folder for reference and troubleshooting.
