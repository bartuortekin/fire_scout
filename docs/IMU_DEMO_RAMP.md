# Kalıcı IMU demo rampası

Branch: `feature/imu-demo-ramp`. Dünya: `firescout_fs01/worlds/industrial_world.sdf`.
Normal workspace: `~/firescout_ws`. Model adı: `imu_demo_ramp`.

## 8 Kasım canlı test sonuçları

İlk denemede yalnızca FSM komutlarıyla robot
0.279825 m ilerledi; iki teker ayrı ayrı yaklaşık 4.0023 rad döndü. Ön mesafe
1.772→1.498 m oldu. **LiDAR CLEAR kalırken EXPLORE'un `front_m > 1.50` hareket
koşulu ilerlemeyi durdurdu.** Bu, sonraki mesafe düzeltmesinden önceki sonuçtur.
Kamera STALE kaynaklı ayrı geçici SAFE_STOP duruşları da kayıtta ayrıştırıldı.

Ayrı doğrudan yerleştirmede gerçek −20°/WARNING → FSM SAFE_STOP, rampada kısa
hareket-izni kontrolünde sıfır komut ve düzde NORMAL dönüşü doğrulandı. Bu sonuç
tırmanabilirlik kanıtı değildir.

Sonraki FSM düzeltmesi, CLEAR olan 1.20–1.50 m aralığında mevcut CAUTION durumunu
seçer; sensör eşikleri ve hareket politikasının güvenlik payları aynı kalır.
Gerçek tekrarda front=1.498 m iken CAUTION/0.02 m/s ile eski duruş noktası geçildi.
Robot tekerlekleriyle yaklaşık 1.158 m ilerledi; pitch≈−15.13° olduğunda kamera
SEARCHING iken IMU WARNING → FSM SAFE_STOP ve hız sıfır doğrulandı.
**Tam rampa tırmanışı/platoya ulaşma doğrulanmadı.**

[Seçilmiş test kanıtları ve sınırlar](VALIDATION_RESULTS.md).
Tam yerel kayıtlar `evidence/imu_demo_ramp_fsm_2026-11-08_run01/` ve
`evidence/fsm_clearance_fix_2026-11-08/` altında korunur; büyük bag/video arşivi
küçük Git kanıt seçimine dahil değildir.

## Yerleşim ve geometri

Rampa doğu taraftaki ayrı demo şeridinde, +Y yönünde yükselir:

| Özellik | Değer |
|---|---|
| Merkez hattı | x=2.90 m |
| Kapladığı alan | x=2.45…3.35, y=−0.25…2.25 m |
| Genişlik / yatay uzunluk | 0.90 / 2.50 m |
| Giriş geçişleri | 5°, 10°, 15°; her biri yatayda 0.15 m |
| Ana eğim | 20°; yatayda 1.00 m, y=0.20…1.20 |
| Üst geçişler | 15°, 10°, 5°; her biri yatayda 0.15 m |
| Üst düz platform | 0.60 m; yaklaşık 0.5235 m yükseklikte |
| Yüzey | Mavi, statik; 8 eşleşen görsel/çarpışma kutusu, kalınlık 0.04 m |

Kutuların merkezleri değil **üst yüzeyleri** uç uca hizalıdır. Girişin üst ucu
zeminde z=0'dan başlar, kalınlık zeminin altına gömülür; robotun önünde 4 cm'lik
bir basamak oluşmaz. Komşu yüzey açıları en fazla 5° değişir. Bu, parçalı düzlemsel
bir geçiştir; matematiksel olarak kesintisiz eğrilikli bir yüzey değildir.
Üst platformun kuzey ucunda iniş rampası yoktur; oradan sürerek çıkış planlanmaz.

Robotun tekerlekler dahil genişliği yaklaşık 0.345 m, tahrik tekeri yarıçapı
0.07 m, arka destek yarıçapı 0.025 m, destek açıklığı yaklaşık 0.23 m'dir.
Gövde çarpışma kutusunun altı düz zeminden 0.09 m yüksektedir. 0.90 m genişlik
her yanda yaklaşık 0.278 m pay bırakır; kademeli açı geçişleri dik eşik yerine
tekerin yüzeye yaklaşmasını sağlar. Bu boyut hesabı fiziksel sürüş kanıtı değildir.

Başlangıçtaki +X ana yolundan (y≈−1.8) ve kırmızı panel test şeridinden
(x≈−2.8) ayrıdır. `crate_two` ile yatayda 0.825 m, sağ duvarın iç yüzüyle
0.575 m, arka duvarla 0.675 m boşluk vardır. Mavi renk kırmızı nesne testiyle
karışmaz. Eski dünya modelleri, robot, sensörler, FSM ve eşikler değiştirilmedi.

## LiDAR ve FSM etkileşimi

- Çarpışmalar fizik motoruna ve sensörlere açıktır; rampayı LiDAR'dan gizleyen
  maske veya sahte mesafe yoktur. Rampa girişine bakarken yatay tarama eğimli
  yüzeyi engel olarak algılayabilir. Düz zemindeki tarayıcı yüksekliği 0.32 m'dir.
- LiDAR WARNING → CAUTION, DANGER → AVOID davranışına yol açabilir. CLEAR iken
  ön mesafe <=1.50 m ise FSM de CAUTION seçer. FSM ayrıca
  CAUTION'da ön mesafe <=0.80 m olduğunda ileri hareket vermez. Bu nedenle
  FSM'nin rampanın tamamını tırmanacağı garanti değildir.
- IMU ölçütü `max(abs(roll), abs(pitch))`; >=15° WARNING, <=12° NORMAL,
  arada histerezis vardır. Bunlar demo eşikleridir; fiziksel devrilme sınırı değildir.
- FSM'de IMU durumu NORMAL değilse, daha öncelikli temas/tehlike latch'i yokken
  SAFE_STOP seçilir; hareket politikası sıfır hız verir. 20° bölümde durması
  beklenen davranıştır. Tam tepeye çıkmak için eşiği yükseltme veya uyarıyı gizleme.
- Kamera STALE veya eski sensör/mesafe verisi de SAFE_STOP sebebi olabilir.
  Önceki testte kamera akışında kesintiler görüldü; duruş nedenini
  `/firescout/fsm/event` içindeki sensör durumlarıyla ayırt et.
- FSM'nin `motion_enabled` varsayılanı false. Bu parametre false iken sıfır hız
  görmek tek başına IMU'nun hareketi durdurduğunu kanıtlamaz; state/event de izlenmeli.

## Başlatma

Dosya değişikliği açık Gazebo'ya kendiliğinden eklenmez. Canlı testlerde açık
tek oturumdaki geometri kullanıldı; bu dokümantasyon hazırlığında yeniden
başlatma veya sürüş yapılmadı. Sonraki normal başlangıçta dünyayı yüklemek için
uygun zamanda mevcut launch'ı kendi terminalinden
Ctrl+C ile kapat, kapandığını kontrol et, ardından **tek** oturum başlat.

Ubuntu'nun kendi terminalinde:

```bash
source /opt/ros/lyrical/setup.bash
cd ~/firescout_ws
colcon build --packages-select firescout_fs01
source install/setup.bash
unset GTK_PATH GIO_MODULE_DIR GDK_PIXBUF_MODULE_FILE GDK_PIXBUF_MODULEDIR QT_QPA_PLATFORMTHEME
export QT_QPA_PLATFORM=xcb QT_STYLE_OVERRIDE=Fusion
ros2 launch firescout_fs01 simulation.launch.py sim_mode:=vm
```

Launch Gazebo/RViz/bridge/modeli başlatır; monitor'leri ve FSM'yi otomatik açmaz.
Her yeni terminalde iki setup dosyasını source et. `ros2 node list` ile kontrol et;
yalnızca eksik olan node'ları ayrı terminallerde çalıştır:

```bash
ros2 run firescout_fs01 imu_monitor.py
ros2 run firescout_fs01 lidar_monitor.py
ros2 run firescout_fs01 camera_monitor.py
ros2 run firescout_fs01 firescout_fsm.py
```

Bu dört komut dört ayrı terminal içindir. Aynı monitor/FSM'den ikinci kopya açma.
FSM açılışta hareketi devre dışı tutar. İzlemek için ayrı terminallerde:

```bash
ros2 topic echo /firescout/imu/tilt_status
ros2 topic echo /firescout/fsm/state
ros2 topic echo /firescout/fsm/event
ros2 topic echo /cmd_vel
```

Grafik: `ros2 run rqt_plot rqt_plot /firescout/imu/roll_deg/data /firescout/imu/pitch_deg/data`.

## A — Fiziksel sürüş testi (yaklaşma ve eğim duruşu doğrulandı)

1. Düz yaklaşma hedefi `(2.90, −0.95)` m, yaw=+90°; robotun önü +Y'ye bakar.
   Başlangıçtaki `(0,−1.8)` konumundan buraya geliş de henüz test edilmiş değildir.
2. Tahrik tekerlerinin dönmesiyle zeminden başlayıp 5°/10°/15° geçişlerden
   yükseldiğini Gazebo'da gözle. Bir model yerleştirme servisiyle bu bölümü atlamak
   fiziksel sürüş testi sayılmaz. Kayma, gövde/bumper teması ve tekerin takılmasını izle.
3. Tek hareket otoritesi kullan. FSM testinde ikinci teleop veya `ros2 topic pub`
   ile /cmd_vel üzerine yarışan komut verme. `ros2 topic info /cmd_vel --verbose`
   ile yayıncıları kontrol et. Bilerek hareket açılacaksa mevcut FSM üzerinde:

   ```bash
   ros2 param set /firescout_fsm motion_enabled true
   ```

   Bu komut robotun hareket etmesine izin verir; 8 Kasım kontrollü testinde kullanıldı.
   EXPLORE hızı 0.04 m/s, CAUTION hızı 0.02 m/s'dir. LiDAR rampaya kaçınma tepkisi
   verebilir; otonom tırmanışın gerçekleşmemesi tek başına rampa geometrisinin
   bozuk olduğunu göstermez. SAFE_STOP ve event sebebini kaydet.
4. Taze IMU WARNING ve ilgili FSM SAFE_STOP/zero Twist gözlenirse eğim güvenliği
   için kanıt kaydet. İlk duruş LiDAR/kamera/temas nedeniyle olmuşsa bunu IMU'nun
   durdurması olarak sunma. Test bitiminde `motion_enabled false` yap.

## B — Doğrudan eğimli yere yerleştirme (8 Kasım'da doğrulandı)

Bu yol tırmanabilirliği değil, gerçek modelin yerçekimi/temas altında IMU ölçümünü
ve FSM tepkisini sınar. FSM varsa önce hareketi kapat; başka hareket yayıncısı
olmadığını kontrol et. Aşağıdaki poz, ana 20° bölümün ortasına az yukarıdan
yerleştirir; gerçek yüzeye oturması için beklenir. Dünya yüklü olmalı.

```bash
ros2 param set /firescout_fsm motion_enabled false
gz service -s /world/industrial_world/set_pose/blocking \
  --reqtype gz.msgs.Pose --reptype gz.msgs.Boolean --timeout 5000 \
  --req 'name: "firescout_fs01" position {x: 2.9 y: 0.7 z: 0.30} orientation {x: 0.12278780396897285 y: -0.12278780396897285 z: 0.6963642403200189 w: 0.6963642403200189}'
```

FSM yoksa parametre komutunu atla; yalnızca test için ikinci FSM başlatma.
Yerleşme sonrasında beklenen değerler roll≈0°, pitch≈−20°, IMU WARNING'dir.
FSM'nin öteki girdileri tazeyse ve latch yoksa SAFE_STOP beklenir. Serviste
`data: true` görülmesi testin geçtiği anlamına gelmez: gerçek `/imu/data`, açı,
durum, model duruşu ve uygun FSM event'i beraber kontrol edilmelidir.

Sonra hareket kapalıyken başlangıç zeminine dönüş:

```bash
gz service -s /world/industrial_world/set_pose/blocking \
  --reqtype gz.msgs.Pose --reptype gz.msgs.Boolean --timeout 5000 \
  --req 'name: "firescout_fs01" position {x: 0 y: -1.8 z: 0.03} orientation {w: 1}'
```

Yerleşince gerçek roll/pitch≈0° ve NORMAL dönüşünü kontrol et. IMU SAFE_STOP
tek başına latch değildir; öteki koşullar uygunsa NORMAL sonrası kalkabilir.
Temas, kırmızı tehlike veya AVOID-timeout latch'i varsa davranış farklıdır.

## Bu değişiklikte yapılan / yapılmayan kontroller

Yapılanlar: dünya için `gz sdf -k`, XML/benzersiz adlar, çarpışma-görsel eşleşmesi,
üst yüzeylerin sürekliliği, giriş/çıkış açı farkları, genişlik ve uzunluk, duvar/
kutu/ana yol boşlukları; başlangıç LiDAR ön sektörü ve kırmızı panel doğrultusunda
analitik ışın-kutu kontrolleri. Bunlar gerçek `/scan` ölçümü yerine geçmez.
Mevcut FSM/sensör testleriyle birlikte otomatik testler ve paket derlemesi de
çalıştırılır; sonuç son çalışma özetinde belirtilir.

8 Kasım'da bu kalıcı rampaya **tekerlekli yaklaşma** ve ayrı doğrudan yerleştirme
testleri yapıldı; gerçek LiDAR etkileşimi ve canlı IMU→FSM duruşu kaydedildi.
**Tam fiziksel tırmanış doğrulanmadı.** Önceki geçici platform kanıtları ve yeni
doğrudan yerleştirme, tekerlekli tırmanış başarısı olarak sunulmaz. Hiçbir eşik
değiştirilmedi; kamera sürekliliği sorunu bu testte çözülmedi.

SDF'de görsel ve fiziksel geometri ayrımı:
[SDFormat collision/visual açıklaması](https://sdformat.org/tutorials/specification/spec_shapes/).
