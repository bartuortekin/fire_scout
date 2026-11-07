# PR başlığı

IMU izleme, eğim uyarısı ve fiziksel Gazebo test kanıtları

Hedef: `main` — Kaynak: `feature/imu-monitor`

## PR açıklaması

FireScout IMU verisi artık tazelik ve quaternion geçerliliği kontrol edilerek
izleniyor. Taze ve geçerli yönelimden roll/pitch derece olarak yayımlanıyor;
geçersiz/bayat veride açı yayını kesiliyor ve eğim durumu UNKNOWN oluyor.
15°/12° histerezisli demo uyarısı ve ayarlanabilir 10 Hz grafik çıktıları eklendi.

- `ament_cmake` kurulum kuralı ve Python/mesaj bağımlılıklarıyla
  `ros2 run firescout_fs01 imu_monitor.py` destekleniyor.
- Gerçek Gazebo modelini geçici 20° platforma yerleştiren tekrarlanabilir test
  yardımcısı, SDF fikstürü, test rehberi ve teslim kanıtları eklendi.
- Ekran görüntülerinde eğik model/WARNING, rqt_plot'ta pitch≈−20° ve düz
  model/NORMAL doğrulandı. Manuel çekimler ilk otomatik bag koşusunun ardından
  aynı Gazebo oturumunda yapılan ayrı tekrara aittir.
- Yerel RViz değişikliği bu katkıya dahil edilmedi. Tek MCAP ile aşama etiketli
  JSONL tutuldu; aynı verileri çoğaltan teslim ZIP'i Git dışında bırakıldı.

### Doğrulama

- Normal workspace: `~/firescout_ws`; derleme ve `ros2 run` daha önce doğrulandı.
- Commit öncesi `python3 -m unittest discover -s firescout_fs01/test -v`:
  21 test geçti; tazelik, quaternion, negatif açılar, tam eşikler, histerezis,
  geçersiz/bayat veri ve toparlanma kapsanıyor.
- **Fiziksel simülasyon eğim testi tamamlandı:** gerçek `/imu/data` ile
  düz/NORMAL → 20° platform/WARNING → düz/NORMAL. Her 12 saniyelik pencerede
  beklenen durumda 120 durum mesajı; pitch yaklaşık 0° / −20° / 0°.
- MCAP tümüyle okundu: 24.795 mesaj. Görüntü kopyaları, kanıt dosyalarının
  SHA256 özetleri, Python/XML ve `git diff --check` kontrolleri doğrulandı.

Kanıtlar: [sonuç raporu](../evidence/imu_physical_2026-11-07_run01/RESULTS.md),
[test rehberi](IMU_PHYSICAL_TEST.md).

### İnceleme ve sınırlar

Eğim ölçütü `max(abs(roll), abs(pitch))`; toplam fiziksel yatıklık açısı değildir.
12°/15° değerleri demo eşikleridir; robotun fiziksel devrilme sınırları değildir.
Robot platforma yerleştirildi; rampaya sürüş veya gerçek donanım testi yapılmadı.
`/cmd_vel` yayını ve hareket kontrolü eklenmedi.

**Main'e merge edilmemeli: ekip incelemesi ve ortak entegrasyon testi bekleniyor.**
