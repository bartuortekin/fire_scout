# Alçak bozuk zemin demosu

Normal workspace `~/firescout_ws`. Mevcut 20° `imu_demo_ramp` korunur; bu demo
ondan ve başlangıçtaki ana yoldan ayrı, `y=-0.90 m` merkezli +X şeridindedir.
Dünya: `firescout_fs01/worlds/industrial_world.sdf`.
Canlı sonuçlar: [doğrulama ve seçilmiş kanıtlar](VALIDATION_RESULTS.md).
Tam yerel arşiv `evidence/rough_ground_2026-11-08/RESULTS.md` altında korunur;
bag/video dosyaları küçük Git kanıt seçimine dahil değildir.

| Boyut | Gerekçe |
| --- | --- |
| Yükseklik 0.020 m | 0.07 m tahrik tekeri yarıçapının %29'u, 0.025 m arka desteğin altında |
| Uzunluk 0.60 m | 0.23 m tahrik–arka destek mesafesinden uzun; iki uçta yumuşak geçiş |
| Genişlik 0.80 m | 0.345 m tekerlekli genişliğe her yanda yaklaşık 0.228 m pay |
| Maksimum yüzey eğimi 5.911° | Mevcut 15° demo uyarısının altında; gerçek dinamik IMU açısını garanti etmez |
| Gövde altı açıklığı 0.09 m | 0.02 m tümsek bu açıklığın üçte birinden küçük |

Profil `z(x)=0.01*(1-cos(2*pi*x/0.60))`, `0<=x<=0.60`, 24 eşit yatay
parçayla yaklaşılır. Bu, parçalı düzlemsel bir yüzeydir. İlk ve son yüzey açıları
yalnızca 0.781°; en yüksek tepe 2 cm, iki uçta üst yüzey tam z=0'dadır.
15 mm kalınlık girişte zeminin altına gömülür; 15 mm'lik dik basamak oluşmaz.
Her parçanın görseli ve fiziksel çarpışması aynı poz ve kutu ölçülerini kullanır.
Yeşil renk kırmızı nesne testini taklit etmez. Sürtünme rampayla aynı 1.1'dir.

İlk tümsek `x=-2.70…-2.10`, `y=-1.30…-0.50` alanındadır. Yaklaşma
`(-3.30,-0.90)`, yaw=0; tek tümseğin tam geçiş hedefi `x>=-1.80`.
Bu hedef gövdenin arka ucunu da tümseğin dışına çıkarır. Başlangıca yerleştirme
hareket kapalıyken yapılır; bu, üzerinden geçiş testi sayılmaz. Geçiş sırasında
poz değiştirilmez ve yalnızca FSM'nin `/cmd_vel` komutları kullanılır.

Tek tümseğin gerçek geçişi doğrulandıktan sonra aynı profil 1.00 m merkez
aralığıyla beş tümseğe genişletildi: 0.60 m tümsek + 0.40 m düz ara. Düz ara hem destek açıklığından
hem de tekerlek çapından uzundur. Beşli yolun son ucu x=1.90 m, tam gövde geçiş
hedefi x>=2.20 m olur. Kuzeydeki kutulara, doğudaki 20° rampaya veya y=-1.8
başlangıç koridoruna taşmaz. Tek geçişte 1.501 m / en büyük mutlak pitch 4.62°;
beşli geçişte 5.501 m / 4.70° ve beş tümseğin tam geçişi kaydedildi.

Beşli testte kayıt altyapısı için yaklaşık 75 saniyelik kontrollü hareket-kapalı
ara verildi; aynı ölçüm süreciyle devam edildi. Bu, kesintisiz otonom sürüş değildir.
Kamera/LiDAR STALE duruşları ve kısa IMU UNKNOWN aralığı ayrıca raporlandı.
Kamera tazelik sorunu sürüyor; korumalar veya sensör eşikleri değiştirilmedi.

Sensör ve hareket korumaları aynen geçerlidir. Ön mesafe nedeniyle CAUTION,
DANGER/AVOID, IMU WARNING veya kamera/LiDAR STALE nedeniyle SAFE_STOP olabilir.
Her duruş FSM'nin kendi event metniyle yorumlanmalıdır. Önceki FSM 1.50 m
CAUTION düzeltmesi korunur; bu demo için eşik veya robot kontrol kodu değişmez.

Gövde takılması şu iki bağımsız gözlemle değerlendirilir: gerçek dünya pozunda
tümseğin arkasına kadar tekerlekli ilerleme ve poz/yönelimden hesaplanan tüm
gövde kutusunun en alt noktasının yüzeyden yukarıda kalması. Her örnekte
`body_bottom_z - 0.020` muhafazakâr açıklık alt sınırıdır; bütün tümseklerin
en yüksek yüzeyini kullanır. Poz tazeliği ayrıca kaydedilir. Bu hesap gövde
kutusuna aittir; yalnızca ön bumper'da bulunan temas sensörü tam gövde temas
sensörü gibi sunulmaz. IMU, tekerlek eklem açıları, gerçek model pozu,
LiDAR sektörleri, kamera durumu, FSM ve hız aynı kayıtlarla incelenir.

Açık Gazebo oturumuna, dünya dosyasından çıkarılan aynı model servisle eklenerek
test yapılabilir; ikinci Gazebo gerekmez. Dosya değişikliği açık dünyayı kendisi
güncellemez. Sonraki normal başlatmada yeni dünya doğrudan yüklenir:

```bash
source /opt/ros/lyrical/setup.bash
cd ~/firescout_ws
colcon build --packages-select firescout_fs01
source install/setup.bash
ros2 launch firescout_fs01 simulation.launch.py sim_mode:=vm
```

Bu başlatma komutu mevcut oturum kapatıldıktan sonra kullanılmalıdır. Her
monitor/FSM için önce `ros2 node list` kontrol edilir; yalnızca eksik kopya
başlatılır. Grafik uygulamaları Ubuntu'nun kendi terminalinde açılır:

```bash
source /opt/ros/lyrical/setup.bash
source ~/firescout_ws/install/setup.bash
unset GTK_PATH GIO_MODULE_DIR GDK_PIXBUF_MODULE_FILE GDK_PIXBUF_MODULEDIR QT_QPA_PLATFORMTHEME
export QT_QPA_PLATFORM=xcb QT_STYLE_OVERRIDE=Fusion
ros2 run rqt_plot rqt_plot /firescout/imu/roll_deg/data /firescout/imu/pitch_deg/data
```

Beşli yolu yeniden sınamak için, tek monitor/FSM kopyası ve tek simülasyon açıkken,
hareket kapalı yaklaşma yerleştirmesi:

```bash
ros2 param set /firescout_fsm motion_enabled false
gz service -s /world/industrial_world/set_pose/blocking \
  --reqtype gz.msgs.Pose --reptype gz.msgs.Boolean --timeout 15000 \
  --req 'name: "firescout_fs01" position {x: -3.3 y: -0.9 z: 0.03} orientation {w: 1}'
```

`data: true` yanıtını, modelin zemine oturmasını ve güncel IMU NORMAL / kamera
SEARCHING / LiDAR verisini doğrula. `/cmd_vel` yayıncısı yalnızca FSM olmalı.
Tam geçiş hedefi x>=2.20 m; robot buraya gelince hareketi kapat. Kayıtlar bu
konumu gerçek Gazebo dünya pozundan ölçer; odometri tek başına geçiş kanıtı değildir.

Kontrollü sürüş izni `ros2 param set /firescout_fsm motion_enabled true`;
iş bitince mutlaka `ros2 param set /firescout_fsm motion_enabled false`.
Başka `/cmd_vel` yayıncısı kullanılmaz. Otomatik geometri testleri fiziksel
geçiş kanıtı değildir; gerçek sonuçlar ve tamamlanamayan aşamalar sonuç notundadır.
