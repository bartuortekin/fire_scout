# FireScout FSM ve zemin testleri: doğrulanan sonuçlar

8 Kasım 2026, VMware, ROS 2 Lyrical / Gazebo Jetty, normal `~/firescout_ws` kurulumu.
Bu not tamamlanmış canlı kayıtların özetidir. Commit hazırlığında Gazebo sürüşü
tekrarlanmadı; otomatik kontroller ayrı belirtilir. Yapay IMU mesajı fiziksel test sayılmaz.

## FSM mesafe düzeltmesi ve gerçek rampa yaklaşması

LiDAR CLEAR eşiği 1.20 m iken EXPLORE hareketi yalnızca >1.50 m'de mümkündü.
FSM artık 1.20–1.50 m aralığında mevcut CAUTION durumuna geçer: 0.02 m/s.
LiDAR 0.70/1.20 m eşikleri, CAUTION'ın 0.80 m duruş payı, AVOID koşulları,
tazelik/temas/tehlike kontrolleri ve IMU 15°/12° histerezisi korunmuştur.

Gerçek tekrarda front=1.498073 m, LiDAR CLEAR, kamera SEARCHING ve IMU NORMAL iken
FSM CAUTION / hız 0.02 m/s gözlendi. Robot 1.158116 m ilerledi; pitch≈−15.126°
olduğunda kamera SEARCHING iken IMU WARNING → FSM SAFE_STOP ve hız 0 doğrulandı.
**Tam 20° rampa tırmanışı veya platoya varış doğrulanmadı.**

- [Gerçek yaklaşma grafiği](../evidence/fsm_clearance_fix_2026-11-08/wheel_approach.png)
- [Ölçüm özeti](../evidence/fsm_clearance_fix_2026-11-08/live_approach/summary.json),
  [FSM olayları](../evidence/fsm_clearance_fix_2026-11-08/live_approach/events.jsonl),
  [kayıt doğrulaması](../evidence/fsm_clearance_fix_2026-11-08/recording_validation.json)

Ayrı doğrudan yerleştirmede gerçek model yaklaşık −20°/WARNING verdi; FSM
SAFE_STOP ve rampada kısa hareket izni açıldığında da hız 0 kaldı. Düz zemine
dönüşte yaklaşık 0°/NORMAL doğrulandı. Bu aşama tekerlekli tırmanış değildir:
[ölçüm özeti](../evidence/imu_demo_ramp_fsm_2026-11-08_run01/summary.json),
[eğim görüntüsü](../evidence/imu_demo_ramp_fsm_2026-11-08_run01/screenshots/03_direct_20deg.png),
[düz zemin görüntüsü](../evidence/imu_demo_ramp_fsm_2026-11-08_run01/screenshots/04_return_flat_disabled.png).

## Tek tümsek ve beşli kısa yol

Tek tümsek geçişi doğrulandıktan sonra dört kopya daha eklendi. Her biri
2 cm yüksek, 60 cm uzun, 80 cm geniş; aralarında 40 cm düz zemin var.
En dik yüzey 5.911°, giriş ve çıkış zemine bağlanır. 20° rampa ayrı alanda korunur.
[Geometri hesabı](../evidence/rough_ground_2026-11-08/geometry.json),
[aynı dünyadaki yerleşim](../evidence/rough_ground_2026-11-08/five_bumps_and_preserved_ramp.png).

| Gerçek ölçüm | Tek tümsek | Tamamlanan beşli deneme |
|---|---:|---:|
| Tam geçen tümsek | 1/1 | 5/5 |
| İleri dünya konumu değişimi | 1.500975 m | 5.501093 m |
| Sol/sağ teker ilerlemesi | 21.4954 / 21.4954 rad | 78.9509 / 78.9509 rad |
| En büyük mutlak pitch | 4.6248° | 4.6967° |
| En büyük mutlak roll | ≈0° | 0.0000021° |
| Gövde açıklığı hesap alt sınırı | ≈5.26 cm | ≈5.26 cm |
| Ön bumper teması | 0 | 0 |
| Kullanılabilir ön sektör aralığı | 2.56291–5.00463 m | 1.72401–5.59975 m |

Yaklaşma noktasına ve son düz zemine yerleştirme hareket kapalıyken yapıldı.
Geçişlerin içinde robot pozu değiştirilmedi; yalnızca FSM /cmd_vel yayımladı.
Gerçek Gazebo dünya pozu ve tekerlek eklem açıları birlikte kullanıldı.
Gövde kutusunun döndürülmüş en alt z noktasından tüm yolun maksimum 2 cm yüzey
seviyesi çıkarılarak muhafazakâr açıklık alt sınırı hesaplandı. Bu hesap örneklenmiş
pozlara aittir; ön bumper sensörü tam gövde temas sensörü gibi sunulmaz.

- Tek: [grafik](../evidence/rough_ground_2026-11-08/single/crossing.png),
  [özet](../evidence/rough_ground_2026-11-08/single/summary.json),
  [olaylar](../evidence/rough_ground_2026-11-08/single/events.jsonl),
  [kayıt kontrolü](../evidence/rough_ground_2026-11-08/single/recording_validation.json).
- Beşli: [grafik](../evidence/rough_ground_2026-11-08/five_retry/crossing.png),
  [özet](../evidence/rough_ground_2026-11-08/five_retry/summary.json),
  [olaylar](../evidence/rough_ground_2026-11-08/five_retry/events.jsonl),
  [kayıt kontrolü](../evidence/rough_ground_2026-11-08/five_retry/recording_validation.json).

Kullanılabilir LiDAR verisinde CLEAR ve ilerlemede EXPLORE/0.04 m/s görüldü.
Bu düşük yol testinde WARNING/DANGER/AVOID tetiklenmedi; bu durumlar için yeni
fiziksel engel testi yapılmış sayılmaz. Geçişi sağlamak için korumalar kapatılmadı.

## Kamera tazelik sorunu ve kontrollü ara

**Kamera tazelik sorunu devam ediyor.** Sürüş evresindeki FSM SAFE_STOP geçişleri:

| Geçiş anındaki durum | Tek tümsek | Tamamlanan beşli deneme |
|---|---:|---:|
| Yalnız kamera STALE | 19 | 152 |
| Yalnız LiDAR STALE | 4 | 72 |
| İkisi birlikte STALE | 0 | 4 |

Sayılar süre veya bağımsız hata sayısı değildir. Beşli ölçüm evresi kontrollü
arayı da içerir. Tek tümsekte IMU NORMAL kaldı. Beşlide t≈709.33–709.72 s
arasında 5 gözlem örneğinde IMU UNKNOWN vardı; kamera/LiDAR tazelik sorunuyla
birlikte FSM zaten SAFE_STOP ve hız 0 idi. Bu bir eğim WARNING olayı değildir.
Grafiklerde kullanılamayan açı/mesafeler güncelmiş gibi çizilmez; farklı topic'ler
atomik bir örnek oluşturmaz. Duruş yorumları FSM'nin kendi olay metinlerine dayanır.

İlk beşli deneme test yardımcısının ROS context-invalid/kapanış hatasıyla kesildi
ve başarılı sayılmadı: [kesinti notu](../evidence/rough_ground_2026-11-08/five/INTERRUPTED.md).
Son denemede üst gözeticinin terminal oturumu SIGTERM ile sonlandı; asıl ölçüm ve
poz okuyucu çalışmayı sürdürdü. Hareket bağımsız parametre komutuyla kapatıldı;
aynı ölçüm sürecine terminalden bağımsız gözetici bağlandıktan sonra devam edildi.
Yaklaşık t=250.82–325.91 s sabit bölüm bu **kontrollü aradır**; kamera duruşu veya
eski FSM mesafe hatası değildir. CSV `motion_enabled` alanı bu dış kapatmada true
kalabilir; gerçek hız 0'dır. Beşli geçiş kesintisiz otonom sürüş olarak sunulmaz:
[kontrollü ara açıklaması](../evidence/rough_ground_2026-11-08/five_retry/CONTROL_PAUSE.md).

## Kontroller ve kanıt kapsamı

Son geometride 101 unittest, `gz sdf -k` ve normal `~/firescout_ws` derlemesi geçti.
Birim testleri 1.50/1.20/0.80/0.70 m sınırlarını, AVOID 1.35 m çıkışını,
STALE/UNKNOWN/eğim ve hareket kapalı korumalarını; geometri testleri ise
süreklilik, boyutlar ve görsel/çarpışma eşleşmesini kapsar. Bunlar canlı sürüş değildir.
Bu dokümantasyon hazırlığındaki yeniden kontroller commit planında ayrıca yazılır.

Beşli kayıtta fotoğraf işlemleri çevresindeki iki poz örneğinin yaşı >1 s idi;
poz grafiği/açıklık hesabından çıkarıldı (t≈509.783, 1148.469 s; en fazla 1.498 s).
Ham veri değişmedi. Kesik denemede 2, son beşli kayıtta 3 transport mesaj kaybı
bildirildi; bag'ler kayıpsız varsayılmaz. Tek ve beşli videolar 60 saniyelik
kesitlerdir; tam sürüşün videosu değildir. Son beşli sürüş evresi 1133.6 s duvar
zamanı aldı; sensör duruşları ve kontrollü ara bu süreye dahildir.

Bu nota bağlı küçük kanıt seçimi grafik, PNG, özet JSON ve olay metinleridir;
ham bag veya video içermez. Özet/grafikler ham veriyle birebir yeniden analiz
edilmek istenirse yerel arşiv gerekir; küçük paket tek başına replay paketi değildir.
Tam CSV/bag/video dosyaları `evidence/fsm_clearance_fix_2026-11-08/`,
`evidence/imu_demo_ramp_fsm_2026-11-08_run01/`, `evidence/rough_ground_2026-11-08/`
altında yerelde korunur. Ayrı indirme/yayın bağlantısı henüz oluşturulmadı.

Testlerin sonunda hareket kapatılıp robot (0,-1.8,0) başlangıcına döndürüldü;
hız sıfır ve IMU NORMAL idi. Son kontrol anında kamera STALE idi:
[bağımsız son kontrol](../evidence/rough_ground_2026-11-08/final_safety_check.json).
Her monitor ve FSM tek kopya; tek hız yayıncısı FSM. Eğim eşikleri demo değerleridir,
robotun fiziksel devrilme sınırı olarak yorumlanmaz. Native Ubuntu, farklı hızlar,
yanal tümsek geçişleri ve tam otonom keşif bu testlerle doğrulanmış değildir.
