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

Kamera, LiDAR ve IMU monitor'ları ile hareket izni başlangıçta kapalı olan FSM mevcuttur.
Normal çalışma alanı `~/firescout_ws`'dir. Haritalama ve tam otonom keşif henüz doğrulanmamıştır.

### 8 Kasım 2026: kayıtlarla doğrulanan davranışlar

| Test | Gerçek Gazebo sonucu |
|---|---|
| FSM mesafe sınırı | Ön mesafe 1,498 m ve LiDAR CLEAR iken CAUTION, 0,02 m/s; eski kalıcı duruş giderildi. |
| 20° rampa | Tekerlekli yaklaşmada pitch −15,13° civarında IMU WARNING → FSM SAFE_STOP ve sıfır hız. Tam rampa tırmanışı doğrulanmadı. |
| Ayrı eğimli yerleştirme | Gerçek modelde yaklaşık −20°/WARNING ve düz zemine dönüşte yaklaşık 0°/NORMAL; tekerlekli tırmanış sayılmaz. |
| Tek alçak tümsek | 1,501 m tekerlekli ilerleme; en büyük mutlak pitch 4,62°. |
| Beş alçak tümsek | Beşi de geçildi; 5,501 m ilerleme, en büyük mutlak pitch 4,70°. Kayıt altyapısı için kontrollü ara içerir. |

Geçişlerde yalnızca FSM `/cmd_vel` yayımladı; sensör eşikleri ve korumalar korunmuştur.
Tümseklerde gövde açıklığının örneklerden hesaplanan alt sınırı yaklaşık 5,26 cm kaldı;
ön bumper teması kaydedilmedi. Bu, tam gövde temas sensörü ölçümü değildir.

**Kamera tazelik sorunu devam ediyor:** kamera/LiDAR STALE durumlarında güvenli duruşlar yaşandı.
Beşli testte kısa IMU UNKNOWN aralığı da sıfır hızla karşılandı. Beşli testteki
yaklaşık 75 saniyelik kontrollü arayı kesintisiz sürüş veya kamera duruşu olarak saymıyoruz.
Testler sonunda hareket kapatıldı ve robot başlangıç konumuna döndürüldü.

Son geometride 101 birim testi, normal workspace derlemesi ve SDF doğrulaması geçti.
Birim testleri fiziksel sürüş kanıtından ayrıdır; bu dokümantasyon hazırlığında
simülasyon sürüşü yeniden yapılmadı.

[Test ayrıntıları ve seçilmiş kanıtlar](docs/VALIDATION_RESULTS.md) ·
[20° rampa rehberi](docs/IMU_DEMO_RAMP.md) ·
[Alçak tümsek yolu rehberi](docs/ROUGH_GROUND_DEMO.md)

## Kurulum ve kullanım

Ayrıntılı kurulum, başlatma ve sensör testleri için:

**[FireScout FS-01 Teknik Dokümantasyonu](firescout_fs01/README.md)**

Eski sürümler hakkında bilgi için:

**[Yedek Dosyalar](backups/README.md)**
