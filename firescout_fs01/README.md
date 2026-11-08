
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

Normal geliştirme workspace'i `~/firescout_ws`'dir. Launch Gazebo, RViz,
bridge ve robot_state_publisher'ı başlatır; kamera/LiDAR/IMU monitor'larını ve
FSM'yi otomatik başlatmaz. Açık oturumu ve `ros2 node list` çıktısını inceleyip
yalnızca eksik node'ları ayrı Ubuntu terminallerinde çalıştır:

```bash
ros2 run firescout_fs01 camera_monitor.py
ros2 run firescout_fs01 lidar_monitor.py
ros2 run firescout_fs01 imu_monitor.py
ros2 run firescout_fs01 firescout_fsm.py
```

Bu komutlar dört ayrı terminal içindir. FSM'nin hareket izni başlangıçta kapalıdır.
FSM testinde tek `/cmd_vel` yayıncısı FSM olmalıdır; mevcut monitor veya Gazebo
kopyası varken ikinci kopya açılmaz.

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

Bu bölümdeki doğrudan hız komutları, FSM çalıştırılmayan ayrı manuel test içindir.
FSM sürüş testinde hareket izni `ros2 param set /firescout_fsm motion_enabled true`
ile açılır ve test sonunda `false` ile kapatılır; aynı anda ikinci hız yayıncısı kullanılmaz.

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

### 8 Kasım 2026: FSM, rampa ve tümsek kayıtları

| Senaryo | Doğrulanan davranış | Sınırı |
|---|---|---|
| 1,498 m ön mesafe | CLEAR → CAUTION ve 0,02 m/s ile gerçek ilerleme | LiDAR eşikleri ve mevcut 0,80 m ileri hareket payı değiştirilmedi. |
| 20° rampaya tekerlekli yaklaşma | Yaklaşık 1,158 m ilerleme; pitch −15,13° civarında WARNING → SAFE_STOP, hız 0 | Tam tırmanış/platoya ulaşma doğrulanmadı. |
| Ayrı 20° yerleştirme | Gerçek IMU WARNING, FSM SAFE_STOP; düz zeminde NORMAL dönüşü | Doğrudan yerleştirme, fiziksel tırmanış değildir. |
| Tek tümsek | 1,501 m ilerleme, en büyük mutlak pitch 4,62° | 2 cm yüksek / 60 cm uzun / 80 cm geniş profil. |
| Beş tümsek | 5,501 m ilerleme, en büyük mutlak pitch 4,70°, beşi de tam geçildi | Kontrollü ara ve sensör tazelik duruşları içerir; kesintisiz sürüş değildir. |

Tekerlekli aşamalarda gerçek Gazebo dünya pozu ve `/joint_states` kullanıldı;
geçiş sırasında model pozu değiştirilmedi. Tek hız yayıncısı FSM idi.
Tümseklerde gövde kutusu için örneklerden hesaplanan açıklık alt sınırı yaklaşık 5,26 cm;
ön bumper temas mesajı yok. Tam gövde temas sensörü bulunmadığı için bu ayrım korunur.

Kamera tazeliği sorunu çözülmedi. Beşli sürüş evresindeki SAFE_STOP geçişlerinde
152 kez yalnız kamera STALE, 72 kez yalnız LiDAR STALE, 4 kez ikisi birlikte görüldü.
Bu sayılar süre veya bağımsız hata sayısı değildir; kontrollü arayı da kapsayabilir.
Kısa bir IMU UNKNOWN aralığında FSM zaten SAFE_STOP ve hız sıfırdı.
Eğim WARNING kaynaklı bir duruş olarak sayılmadı.

Beşli kayıtta yaklaşık t=250,82–325,91 s boyunca, test gözeticisi oturumu kesildiği
için hareket bilinçli kapatıldı; aynı ölçümle sonra devam edildi. CSV'deki
`motion_enabled` gözlemcinin kendi isteğini tutar ve bu dış kapatma sırasında true
kalabilir. Bu bölümdeki sıfır hızın nedeni bilinçli aradır; eski FSM mesafe hatası değildir.

101 birim testi, normal `~/firescout_ws` derlemesi ve `gz sdf -k` doğrulaması geçti.
Kayıtların ayrıntıları, veri kaybı/örnek tazeliği sınırları ve küçük kanıt seçimi:
[doğrulama notu](../docs/VALIDATION_RESULTS.md).
Bu dokümantasyon hazırlığında canlı sürüş tekrarlanmadı.

## 8. Current Limitations

- Sensor-based FSM exists; mapping and full autonomous exploration have not been validated.
- No actual flame or temperature sensor is included.
- The camera monitor uses a red-object demo; this is not a real flame detector.
- Native Ubuntu launch mode has not yet been tested.
- Physics and robot geometry may require further tuning.
- Camera/LiDAR freshness interruptions remain; the five-bump run also included a controlled pause.
- Full climbing of the 20-degree ramp has not been demonstrated; the existing tilt guard stops motion.

## 9. Project Files

- `urdf/firescout.urdf.xacro` — Robot model
- `worlds/industrial_world.sdf` — Gazebo environment
- `config/bridge.yaml` — ROS 2 / Gazebo topic bridges
- `launch/simulation.launch.py` — Simulation launcher
- `rviz/firescout.rviz` — RViz configuration

Previous versions are stored in the repository's `backups/` folder for reference and troubleshooting.
