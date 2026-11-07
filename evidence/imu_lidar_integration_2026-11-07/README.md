# IMU + LiDAR ortak canlı kontrolü — 7 Kasım 2026

`feature/imu-monitor`, LiDAR PR #2'yi içeren `origin/main` (`ad10f5c`) ile yerel
olarak merge edildi. Çakışma çıkmadı. CMake her iki monitor'ü kuruyor; paket
bağımlılıkları zaten uyumlu. IMU/LiDAR uygulama dosyaları ve testleri kendi
branch sürümleriyle bayt bayt aynı kaldı.

- Normal `~/firescout_ws` içinde `colcon build --packages-select firescout_fs01`
  geçti. Mevcut CMake <3.10 uyumluluk uyarısı devam ediyor.
- `python3 -m unittest discover -s firescout_fs01/test -v`: **30 test geçti**
  (21 IMU + 9 LiDAR).
- Mevcut Gazebo/RViz/bridge oturumu kullanıldı; simülasyon yeniden başlatılmadı,
  model taşınmadı, yapay sensör mesajı veya hareket komutu yayımlanmadı.
- Önceden çalışan tek `lidar_monitor` korundu. Yalnızca eksik `imu_monitor`
  normal workspace'ten `ros2 run` ile başlatıldı; ikinci kopya oluşturulmadı.

## Gerçek veri sonucu

12.00 saniyelik hazır durumdaki ortak ölçüm penceresi:

| Veri/çıktı | Sonuç |
|---|---|
| Gerçek `/imu/data` | 197 mesaj; tek yayıncı `ros_gz_bridge` |
| Gerçek `/scan` | 31 mesaj; tek yayıncı `ros_gz_bridge` |
| IMU eğim durumu | 120 × NORMAL |
| LiDAR durumu | 120 × CLEAR |
| Roll / pitch | yaklaşık 0° / 0°; VALID, belirsizlik bilinmiyor |
| Ön / sol / sağ yayımlanan mesafe | 3.6635 / 1.3682 / 8.0000 m |

Açı ve her sektör mesafesi kanalında 120'şer mesaj alındı. Son yayımlanan açılar,
aynı anda dinlenen gerçek quaternion dönüşümüyle 0.02° içinde; sektör çıktıları
gerçek LaserScan sektör sonuçlarıyla 0.02 m içinde karşılaştırıldı. LiDAR'ın açık
alanı sensör maksimum menzilinde çizme kuralı karşılaştırmada dikkate alındı.
Kontrol sonunda alınma yaşı en fazla 0.238 saniyeydi. Her çıktı kanalında tek
yayıncı ve her monitor adından tek node olduğu doğrulandı.

`summary.json` sayısal sonuçları, mesaj sayılarını ve yayıncı listesini içerir.
`imu_monitor_excerpt.log` ortak kontrolden sonraki sabit log kesitidir.
Kontrol bitiminde iki monitor de açık bırakıldı; yeni IMU sürecinin canlı logu
`~/fire_scout/log/imu_lidar_integration/imu_monitor.log`, ros2 wrapper PID kaydı
`/tmp/firescout_joint_imu_monitor.pid` altındadır.

## İlk deneme ve korunan yerel veriler

İlk kontrol, IMU başlangıcı için yalnızca beş saniye bekledi; mesaj tipi yükleme
henüz tamamlanmadan araç zaman aşımına uğradı ve kendi başlattığı IMU'yu kapattı.
Bu deneme başarılı sayılmadı; logu `attempt01_startup_timeout.log` içinde korundu.
Uygulama değiştirilmedi. Kontrol aracı gerçek çıktılar hazır olana kadar (en fazla
45 saniye) bekleyecek şekilde düzeltildi; yukarıdaki sonuç sonraki başarılı denemedir.
Önceden çalışan LiDAR bu süreçte durdurulmadı.

Main üzerinde takip edilmeyen 799.007 baytlık teslim ZIP'i branch geçişini
engellemedi; taşınmadan korundu. Öncesi/sonrası SHA256:
`87a631eab29b9fd9ffce818e9f6a2d636000e4bce0d37ee166576a6e5d31e769`.
Önceden var olan `Local RViz settings before integration` stash'i korundu ve
uygulanmadı. Main'e yerel veya GitHub üzerinde merge ve push yapılmadı.
