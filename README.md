# Fire Scout

**Introduction to Mobile Robotics — Midterm Project**

Fire Scout, tehlikeli ve yangın riski taşıyan endüstriyel ortamların keşfi için geliştirilen ROS 2 ve Gazebo tabanlı bir mobil robot simülasyonu projesidir.

Proje üç kişilik bir ekip tarafından geliştirilmektedir.

## Geliştirme ortamı

- Ubuntu 26.04
- ROS 2 Lyrical
- Gazebo Jetty
- Python, URDF/Xacro, SDF
- RViz 2
- ros_gz_bridge

## Proje yapısı

- `firescout_fs01/` — Güncel ROS 2 paketi, robot modeli, sensörler ve simülasyon
- `backups/` — Önceki sürümlerin yedekleri
- `.gitignore` — Derleme çıktıları ve geçici dosyaların hariç tutulması

## Mevcut durum

VMware üzerinde Gazebo, RViz, diferansiyel sürüş ve dört sensörün temel çalışması test edilmiştir.

LiDAR, RGB kamera, IMU ve Contact sensörlerinin ROS 2 bağlantıları doğrulanmıştır.

VMware için tek komutla simülasyon başlatma testi başarılıdır. Native Ubuntu / Dual Boot modu henüz ekip tarafından doğrulanmamıştır.

Otonom keşif ve karar mekanizması geliştirme aşamasındadır.

## Kurulum ve kullanım

Ayrıntılı kurulum, başlatma ve sensör testleri için:

**[FireScout FS-01 Teknik Dokümantasyonu](firescout_fs01/README.md)**

Eski sürümler hakkında bilgi için:

**[Yedek Dosyalar](backups/README.md)**
