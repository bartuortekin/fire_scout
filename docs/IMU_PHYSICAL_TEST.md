# Gerçek Gazebo IMU eğim testi

Normal workspace `~/firescout_ws`, repo `~/fire_scout`, branch `feature/imu-monitor`.
Eski `/tmp/firescout_imu_check` kurulumu kullanılmaz.

## Tamamlanan koşu ve ekran görüntüleri

7 Kasım 2026'da gerçek model ve gerçek `/imu/data` üzerinden 0°/NORMAL →
−20°/WARNING → 0°/NORMAL sırası doğrulandı; her 12 saniyelik pencerede beklenen
durumda 120 mesaj kaydedildi. Ardından aynı oturumda robot platforma yeniden
yerleştirilip WARNING durumunda, sonra düz zeminde NORMAL durumunda bekletilerek
kullanıcının ekran görüntüsü alması sağlandı. rqt_plot açıldı ve topic aboneliği
doğrulandı. Bu manuel çekimler otomatik bag koşusundan sonraki ayrı tekrardır.

- [Sonuç raporu ve ölçümler](../evidence/imu_physical_2026-11-07_run01/RESULTS.md)
- [Gazebo + WARNING](../evidence/imu_physical_2026-11-07_run01/screenshots/02_ramp_WARNING_gazebo_terminal.png)
- [rqt_plot: pitch≈−20°, roll≈0°](../evidence/imu_physical_2026-11-07_run01/screenshots/02_ramp_WARNING_rqt_plot.png)
- [Gazebo + NORMAL](../evidence/imu_physical_2026-11-07_run01/screenshots/03_flat_NORMAL_gazebo_terminal.png)

Görüntüler açılıp incelendi, orijinalleriyle bayt bayt karşılaştırıldı. Otomatik
screenshot servisinin PNG oluşturmayan önceki denemesi başarılı çekim sayılmadı.

## Yöntem ve sınırları

Mevcut `industrial_world` oturumuna, ayrı SDF dosyasından geçici 20° platform
eklenir. Gerçek `firescout_fs01` modeli platformun üzerine kontrollü yerleştirilir;
yerçekimi, temas fiziği ve modelin kendi IMU sensörü çalışır. Robot rampaya sürülmez.
Bu test eğimli temasta sensör→bridge→node→çıktı zincirini doğrular; tırmanma,
fiziksel devrilme sınırı veya gerçek donanım kalibrasyonu testi değildir.

Tek bir havada poz verme, robot hemen düşeceği için kararlı ölçüm sağlamaz.
Platform yerleştikten sonra 8 saniye beklenir, ardından 12 saniyelik pencere
kaydedilir. 20° seçimi 15° demo uyarı eşiğinin belirgin üzerindedir.
Platform +X yönünde yükseldiğinden beklenen pitch yaklaşık **-20°**'dir;
uyarı ölçütü mutlak değer kullandığından işaret sonucu değiştirmez.

Sıra: düz/NORMAL → platform/WARNING → düz/NORMAL. Her pencerede en az 20 ham
IMU mesajı, her açı/durum kanalında en az 5 mesaj, doğru durum ve düzde <3°,
platformda |roll|<3° ve 17°<|pitch|<23° aranır. Bunlar bu testin kabul aralıklarıdır.
Ölçüt `max(abs(roll), abs(pitch))` toplam fiziksel yatıklık açısı değildir.

## Tekrarlama

1. Mevcut Gazebo oturumunu kullan; ikinci oturum başlatma. Dünya adı
   `industrial_world`, model adı `firescout_fs01` olmalı. Robot başlangıçta
   `(x,y,z) ≈ (0,-1.8,0)`, roll/pitch/yaw≈0 ve hareketsiz olmalı. Teleop'u durdur.
   Robot başka yerdeyse araç taşımadan önce hata verir; dünyayı sıfırlama.
2. Her terminalde ortamı yükle:

   ```bash
   source /opt/ros/lyrical/setup.bash
   source ~/firescout_ws/install/setup.bash
   cd ~/fire_scout
   ```

3. İstersen testten önce ayrı terminallerde grafik ve durum görünümünü aç:

   ```bash
   ros2 run rqt_plot rqt_plot /firescout/imu/roll_deg/data /firescout/imu/pitch_deg/data
   ```

   ```bash
   ros2 topic echo /firescout/imu/tilt_status
   ```

4. Yeni bir kanıt klasörü seçerek testi çalıştır:

   ```bash
   python3 tools/imu_physical_test.py --output evidence/imu_physical_repeat01
   ```

   Araç çalışan `imu_monitor` varsa onu kullanır; yoksa normal workspace'ten
   `ros2 run` ile başlatır. `/imu/data` için tek yayıncının `ros_gz_bridge`
   olduğunu kontrol eder. Yapay IMU veya `/cmd_vel` yayımlamaz. Var olan kanıt
   klasörünü ezmez. Terminal her ölçüm penceresini bildirir.
5. Test robotu başlangıç yerine geri koyar, yalnızca `imu_test_ramp_20deg`
   platformunu kaldırır ve yalnızca kendisinin başlattığı recorder/monitor'ü kapatır.
   Gazebo/RViz açık kalır. Başarıyı yalnızca `summary.json` içindeki `passed: true`
   ve model pozları ile birlikte değerlendir; servis cevabı tek başına kanıt değildir.

Test yarıda kesilirse önce modelin konumunu ve platformun varlığını kontrol et.
Normal kapanışta `finally` temizliği yapılır; süreç zorla öldürülürse temizliğin
yapıldığı varsayılmamalı. Gerekirse bu başlangıç düzeni için dönüş komutu:

```bash
gz service -s /world/industrial_world/set_pose/blocking \
  --reqtype gz.msgs.Pose --reptype gz.msgs.Boolean --timeout 5000 \
  --req 'name: "firescout_fs01" position {x: 0 y: -1.8 z: 0.03} orientation {w: 1}'
```

## Teslim kanıtları ve ekran görüntüleri

- `bag/`: gerçek `/imu/data`, iki açı, durum ve `/clock` kaydı.
- `samples.jsonl`: ham quaternion, kovaryans ve diğer IMU alanları ile gerçek
  yayınlanan açı/durum mesajları; gerçek geçen süre ve aşama adı içerir.
- `summary.json`: ölçüm pencereleri, mesaj sayıları, açı aralıkları ve geçme sonucu.
- `*_model_pose.txt`: yerleşme sonrasında Gazebo'nun bildirdiği gerçek model pozları.
- `commands.jsonl`: Gazebo yerleştirme komutları ve servis yanıtları.
- `imu_source.txt`: IMU yayıncısının bridge olduğunun kaydı.
- `angles_and_status.png`: kaydedilen yayınlardan çizilen grafik; GUI ekran
  görüntüsü değildir. Kesikli çizgiler 12°/15° demo eşikleridir.
- `imu_monitor.log`: araç monitor'ü kendisi başlattıysa terminal ölçümleri/geçişler.
- `screenshots/`: doğrulanmış manuel Gazebo/WARNING, rqt_plot ve Gazebo/NORMAL PNG'leri
  ile kaynak adları/boyutları/özetlerini veren `README.md`.
  İlk koşuda Gazebo screenshot servisi de denendi; `true` cevabına rağmen PNG
  oluşmadı. `*_screenshot_reply.txt` bu denemeyi saklar; ekran görüntüsü kanıtı
  sayılmaz. Tekrar aracı bu başarısız otomatik çekimi kullanmaz.

Ubuntu'da `Print Screen` → Seçim/Pencere → çekim düğmesi ile kendi ekran
görüntünü alabilirsin. VMware tuşu yakalarsa uygulama menüsünden ekran görüntüsü
aracını aç. Gazebo'da robotu yakınlaştır; rqt_plot ve durum terminalini yanına koy.
Her ölçüm penceresinde robotun duruşu, derece ekseni ve NORMAL/WARNING yazısını
birlikte gösteren görüntüyü kanıt klasöründeki `screenshots/` altına kaydet:
`01_duz_NORMAL.png`, `02_rampa_WARNING.png`, `03_duz_NORMAL.png`.
Grafikteki geçmiş çizgiler tek başına güncel veri kanıtı değildir. İlk kayıtta ve
ekran görüntüsü tekrarında veri kaynağı ve tazelik ayrıca doğrulanmıştır.

MCAP ve aşama etiketli JSONL aynı kanıt dizininde birer kez tutulur. Yerel
`*_submission.zip` arşivi aynı verileri kopyaladığından `.gitignore` ile Git dışında
bırakılır; eski ZIP yeni manuel görüntüleri içermez. Güncel kanıtlar dizindedir.

Bu yardımcı test aracı paket çalışma zamanını, launch/world dosyalarını veya
RViz ayarlarını değiştirmez. Grafik testleri kullanıcı tarafından tamamlanmış,
bu çalışmada rqt_plot canlı topic aboneliğiyle tekrar açılmış ve manuel grafiğin
PNG'si incelenmiştir. Main'e merge öncesinde ekip incelemesi ve ortak entegrasyon
testi hâlâ beklenmektedir.

Servis yaklaşımı: [Gazebo Entity creation](https://gazebosim.org/api/sim/9/entity_creation.html).
Jetty oturumundaki `/create/blocking`, `/set_pose/blocking` türleri ayrıca
yerel `gz service --info` ile doğrulanmıştır.
