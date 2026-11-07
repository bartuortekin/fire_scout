# IMU geliştirme notu — 31 Ekim 2026

## 7 Kasım 2026 güncellemesi

Kalan fiziksel simülasyon eğim testi tamamlandı: mevcut Gazebo oturumundaki gerçek
robot, geçici 20° platforma yerleştirildi. Gerçek `/imu/data` üzerinden düzde
≈0°/NORMAL, platformda ≈−20°/WARNING, tekrar düzde ≈0°/NORMAL doğrulandı.
Her aşamada 8 saniye yerleşme ve 12 saniye ölçüm yapıldı; durum kanalında her
pencerede beklenen durumda 120 mesaj vardı. Yapay IMU veya `/cmd_vel` yayımlanmadı.
Platform kaldırıldı ve robot başlangıç yerine döndürüldü. Normal workspace
`~/firescout_ws` kullanıldı; yeni Gazebo oturumu açılmadı.

- [Test rehberi ve tekrar komutu](docs/IMU_PHYSICAL_TEST.md)
- [Kanıt raporu](evidence/imu_physical_2026-11-07_run01/RESULTS.md): bag, ham veriler,
  model pozları, durum logları, sayısal özet ve kayıttan üretilen grafik.
- 21 otomatik test yeniden geçti. Yerel RViz değişikliği bayt bayt korundu.
- İlk otomatik koşuda rqt_plot GUI'si açılmadı; screenshot servisi `true` cevabına
  rağmen PNG üretmedi. Sonraki manuel tekrarda rqt_plot açıldı, açı aboneliği
  doğrulandı ve gerçek WARNING/NORMAL durumlarında kullanıcı beklenerek görüntü
  aldı. `~/Pictures/Screenshots/ss20.png`, `graph20.png`, `normalTİlt.png` açılıp
  doğrulandı, içerikleri değiştirilmeden kanıt dizininde anlamlı adlarla saklandı.
  Bu tekrar ilk bag koşusundan ayrıdır. Son durumda robot düzde, grafik ve IMU
  terminali açık, geçici platform dünyadadır; bu belge/commit aşamasında bunlara
  müdahale edilmedi.
- IMU uygulaması, launch ve dünya dosyaları değiştirilmedi. Yeni ekler test
  yardımcısı, geçici platform fikstürü, rehber ve kanıtlardır. Yerel RViz değişikliği
  IMU commit'ine dahil edilmez. Yinelenen yerel teslim ZIP'i Git dışında tutulur.
  Main'e merge için ekip incelemesi ve ortak entegrasyon testi beklenir.

Aşağıdaki 31 Ekim notları önceki oturumun kaydıdır.

Bugünkü çalışma burada durduruldu. Branch: `feature/imu-monitor`.
Repo: `~/fire_scout`. **Normal workspace: `~/firescout_ws`**; kaynak paket
workspace'e sembolik bağlantıyla bağlı. Eski `/tmp/firescout_imu_check`
derlemesi kullanılmamalı. IMU çalışması bu branch üzerinde kaydediliyor;
main'e merge edilmiyor.

## Mevcut ilerleme

- `scripts/imu_monitor.py`, `/imu/data` (`sensor_msgs/msg/Imu`) dinliyor;
  ament_cmake kurulumu ve Python çalışma zamanı bağımlılıkları eklendi.
- Tazelik: WAITING / ACTIVE / STALE. `time.monotonic()` ve STEADY_TIME timer'ları
  kullanılıyor; `stale_timeout_sec` varsayılanı 2.0 saniye.
- Yönelim: kovaryansın ilk elemanı -1 ise UNAVAILABLE; tamamen sıfır kovaryans
  belirsizlik bilinmiyor demek. Sonlu quaternion, norm > 1e-12 ve
  |norm - 1| <= 0.001 koşulları aranıyor; kabul edilen quaternion normalize ediliyor.
  Roll/pitch dereceye çevriliyor. Tazelik ile yönelim geçerliliği ayrı.
- Eğim: `max(abs(roll), abs(pitch))`; toplam fiziksel yatıklık açısı değildir.
  >=15° WARNING, <=12° NORMAL; arada önceki durum korunur. Veri yok/bayat/geçersizse
  UNKNOWN; UNKNOWN sonrası ara bölgede WARNING. Bunlar demo eşikleri,
  robotun fiziksel devrilme sınırları değil.
- `/firescout/imu/roll_deg` ve `/firescout/imu/pitch_deg`: Float32, yalnızca taze
  ve geçerli veride. `/firescout/imu/tilt_status`: String, UNKNOWN dahil yayımlanır.
  `publish_rate_hz` başlangıç parametresi 10.0 Hz (1–50 Hz); terminal ölçümleri 1 Hz.
  Durum değişimleri ayrıca bir kez loglanır.
- Launch, RViz ve hareket kontrolü değiştirilmedi; `/cmd_vel` yayını eklenmedi.

## Gerçekten yapılan testler

- Normal `~/firescout_ws` içinde derleme ve `ros2 run` doğrulandı.
  Mevcut CMake minimum sürümü için kullanım dışı kalma uyarısı var.
  Symlink-install için scriptin çalıştırma izni düzeltildi.
- Son otomatik test çalışmasında 21 test geçti: kimlik/bilinen quaternion
  dönüşleri, negatif açılar, q/-q eşdeğerliği, normalizasyon, geçersiz girişler,
  tazelik, histerezis eşikleri/ara bölge, UNKNOWN ve toparlanma, açı yayınını kesme.
- Ayrı ROS test topic'lerinde WAITING/ACTIVE/STALE ve eğim geçişleri;
  INVALID/UNAVAILABLE/STALE sırasında açı yayınlanmaması doğrulandı.
  `use_sim_time:=true` ve ilerlemeyen `/clock` ile kontrol sürdü.
  Açı yayın hızı yaklaşık 9.97 Hz ölçüldü (yapay test kanalında).
- Mevcut Gazebo oturumundan gerçek veri okundu: yaklaşık 0° roll/pitch,
  NORMAL, sıfır kovaryans için belirsizlik bilinmiyor çıktısı görüldü.
  İlk timeout kapanışında SIGINT çakışmasıyla traceback görüldü;
  tek SIGINT ile tekrarlanan kontrol temiz kapandı (çıkış 0).
- Kullanıcı dönüş sırasında angular_velocity.z değişimini, tazelikte
  WAITING → ACTIVE → STALE → ACTIVE geçişlerini ve yapay roll=0°/pitch=20°
  sonucunu ayrıca doğruladı.
- rqt_plot kurulu olduğu kontrol edildi; grafik GUI'si açılıp test edilmedi.
- Commit öncesi 21 otomatik test yeniden çalıştırıldı ve geçti. Python sözdizimi,
  package.xml XML yapısı, scriptin çalıştırma izni ve `git diff --check` kontrol edildi.
  Bu son kontrolde Gazebo fiziksel eğim testi veya grafik GUI testi yapılmadı.

## 31 Ekim'de kalan canlı test (7 Kasım'da tamamlandı)

Gazebo'da robotu bilinen fiziksel roll/pitch açılarına getirerek ölçümleri
karşılaştırmak; 15°'de WARNING, ara bölgede korunma ve 12°'de NORMAL dönüşünü
izlemek. Bu test 31 Ekim'de henüz yapılmamıştı; 7 Kasım fiziksel koşusu yukarıda
kayıtlıdır. Yapay quaternion testleri fiziksel test yerine sayılmaz.
UNKNOWN sırasında yeni açı
yayımlanmaz; grafikte geçmiş çizgilerin kalması güncel ölçüm demek değildir.

## Sonraki başlatma komutları

Her terminalde önce:

```bash
source /opt/ros/lyrical/setup.bash
source ~/firescout_ws/install/setup.bash
```

Simülasyon zaten açıksa onu kullan; **ikinci Gazebo başlatma**. Yeniden başlatmak
gerekirse önce kullanıcıya bildir. Yalnızca simülasyon kapalıysa:

```bash
ros2 launch firescout_fs01 simulation.launch.py sim_mode:=vm
```

Ayrı terminalde okuyucu (mevcut okuyucu varsa ikinci kopyayı başlatma):

```bash
ros2 run firescout_fs01 imu_monitor.py --ros-args -p publish_rate_hz:=10.0
```

Grafik ve durum için ayrı terminallerde:

```bash
ros2 run rqt_plot rqt_plot /firescout/imu/roll_deg/data /firescout/imu/pitch_deg/data
ros2 topic echo /firescout/imu/tilt_status
```

Gerekirse normal workspace'te yeniden derleme ve test:

```bash
cd ~/firescout_ws
source /opt/ros/lyrical/setup.bash
colcon build --packages-select firescout_fs01
source install/setup.bash
cd ~/fire_scout
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s firescout_fs01/test -v
```
