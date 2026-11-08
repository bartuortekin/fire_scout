# Fire Scout

**Introduction to Mobile Robotics — Midterm Project**

FireScout, tehlikeli ve yangın riski taşıyan endüstriyel ortamların keşfi için
üç kişilik bir ekip tarafından geliştirilen ROS 2 ve Gazebo tabanlı mobil robot
simülasyonudur. Diferansiyel sürüş, kamera, LiDAR, IMU ve ön bumper sensörü;
sensör durumlarını değerlendiren bir FSM ile birlikte çalışır. Kırmızı nesne
algılama bir demo senaryosudur; gerçek yangın
algılama veya tam otonom keşif sistemi olarak değerlendirilmez.

## Mevcut özellikler

| Bileşen | İşlev |
|---|---|
| Robot ve simülasyon | İki tahrik tekeri ve arka destek; Gazebo dünyası, ROS bridge ve RViz görünümü. |
| Kamera monitor'ı | Gerçek RGB görüntüsünde kırmızı nesne algılama ve kamera durum çıktısı. |
| LiDAR monitor'ı | Ön/sol/sağ sektör mesafeleri, açıklık yönü ve CLEAR/WARNING/DANGER durumları. |
| IMU monitor'ı | Veri tazeliği, quaternion doğrulama, derece cinsinden roll/pitch ve histerezisli eğim durumu. |
| Ön bumper | Ön temas verisi; tam gövde temas sensörü değildir. |
| FSM | Sensör durumlarına göre sınırlı ileri sürüş, yavaşlama, kaçınma ve güvenli duruş. Hareket başlangıçta kapalıdır. |
| Test alanları | Ayrı 20° IMU rampası ve beş alçak tümsekten oluşan kısa yol. |

FSM durumları: `WAIT_SENSORS`, `EXPLORE`, `CAUTION`, `AVOID`, `RECOVER`,
`HAZARD_STOP`, `SAFE_STOP`. Eğim ölçütü `max(abs(roll), abs(pitch))` kullanır;
bu, toplam fiziksel yatıklık açısı değildir. WARNING ≥15°, NORMAL'e dönüş ≤12°;
bunlar demo eşikleridir, robotun fiziksel devrilme sınırı değildir.

## Geliştirme ortamı

- Ubuntu 26.04 / VMware
- ROS 2 Lyrical
- Gazebo Jetty
- Python, URDF/Xacro, SDF
- RViz 2
- ros_gz_bridge

Normal workspace **`~/firescout_ws`**, repository **`~/fire_scout`**, ROS paketi
**`firescout_fs01`**'dir. VMware modu test edilmiştir; Native Ubuntu / Dual Boot
modu henüz ekip tarafından doğrulanmamıştır.

## Hızlı başlatma

Paketin normal workspace'e kurulduğu mevcut düzen için Ubuntu'nun kendi terminalinde:

```bash
source /opt/ros/lyrical/setup.bash
cd ~/firescout_ws
colcon build --packages-select firescout_fs01
source install/setup.bash
ros2 launch firescout_fs01 simulation.launch.py sim_mode:=vm
```

Launch Gazebo, RViz, robot_state_publisher ve bridge'i başlatır; monitor'ları ve
FSM'yi otomatik açmaz. Açık simülasyon varsa mevcut oturumu kullan. İlk kurulum
için [paket dokümantasyonuna](firescout_fs01/README.md) bak.

Her yeni terminalde ROS ve workspace ortamını yükle:

```bash
source /opt/ros/lyrical/setup.bash
source ~/firescout_ws/install/setup.bash
ros2 node list
```

Aşağıdaki komutlardan yalnızca eksik node'a ait olanı, her biri ayrı terminalde çalıştır:

```bash
ros2 run firescout_fs01 camera_monitor.py
ros2 run firescout_fs01 lidar_monitor.py
ros2 run firescout_fs01 imu_monitor.py
ros2 run firescout_fs01 firescout_fsm.py
```

Kontrollü FSM testinde `/cmd_vel` yayıncısı yalnızca FSM olmalıdır. Hareket izni
açılıp test sonunda kapatılır:

```bash
ros2 param set /firescout_fsm motion_enabled true
# Test tamamlandığında:
ros2 param set /firescout_fsm motion_enabled false
```

Rampa/tümsek yaklaşma konumları ve tekrar test adımları aşağıdaki rehberlerdedir.

## Doğrulanan test sonuçları

8 Kasım 2026 kayıtları, normal `~/firescout_ws` kurulumu ve gerçek Gazebo verisine dayanır:

| Test | Gerçek Gazebo sonucu |
|---|---|
| FSM mesafe sınırı | Ön mesafe 1,498 m ve LiDAR CLEAR iken CAUTION, 0,02 m/s; eski kalıcı duruş giderildi. |
| 20° rampa | Tekerlekli yaklaşmada pitch −15,13° civarında IMU WARNING → FSM SAFE_STOP ve sıfır hız. Tam rampa tırmanışı doğrulanmadı. |
| Ayrı eğimli yerleştirme | Gerçek modelde yaklaşık −20°/WARNING ve düz zemine dönüşte yaklaşık 0°/NORMAL; tekerlekli tırmanış sayılmaz. |
| Tek alçak tümsek | 1,501 m tekerlekli ilerleme; en büyük mutlak pitch 4,62°. |
| Beş alçak tümsek | Beşi de geçildi; 5,501 m ilerleme, en büyük mutlak pitch 4,70°. Kayıt altyapısı için kontrollü ara içerir. |

Tekerlekli testlerde gerçek Gazebo dünya pozu ve `/joint_states` birlikte kaydedildi.
Geçiş sırasında robot pozu değiştirilmedi; yalnızca FSM `/cmd_vel` yayımladı.
Sensör eşikleri ve korumalar korunmuştur.
Tümseklerde gövde açıklığının örneklerden hesaplanan alt sınırı yaklaşık 5,26 cm kaldı;
ön bumper teması kaydedilmedi. Bu, tam gövde temas sensörü ölçümü değildir.

Son geometride **101 birim testi**, normal workspace derlemesi ve SDF doğrulaması
geçti. FSM düzeltmesi ayrı uygulanınca 93 test, dünya değişiklikleri ayrı
uygulanınca 8 geometri testi de geçti. Otomatik kontroller fiziksel sürüş kanıtından
ayrıdır. Testler sonunda hareket kapatıldı ve robot başlangıç konumuna döndürüldü.

[Test ayrıntıları ve seçilmiş kanıtlar](docs/VALIDATION_RESULTS.md) ·
[20° rampa rehberi](docs/IMU_DEMO_RAMP.md) ·
[Alçak tümsek yolu rehberi](docs/ROUGH_GROUND_DEMO.md)

## Proje yapısı ve dokümantasyon

- `firescout_fs01/` — ROS paketi, robot modeli, dünya, monitor'lar, FSM ve testler
- `docs/` — Sensör/demo rehberleri ve doğrulama notları
- `evidence/` — Seçilmiş test kanıtları; büyük yerel arşivlerin tamamı Git'e dahil değildir
- `backups/` — Önceki sürümlerin yedekleri
- `.gitignore` — Derleme çıktıları ve geçici dosyaların hariç tutulması

[Teknik kurulum ve sensör testleri](firescout_fs01/README.md) ·
[Kamera monitor'ı](docs/CAMERA_MONITOR.md) ·
[Doğrulanan sonuçlar](docs/VALIDATION_RESULTS.md) ·
[Yedek sürümler](backups/README.md)
