# Commit kapsamları ve PR hedefi — 8 Kasım 2026

Hazırlık durumudur: **commit/push/merge yapılmadı ve index değiştirilmedi**.
Dosya listeleri yalnızca önerilen kapsamdır; yerel arşivlerden dosya silinmedi.
README'ler ve rehberler gerçek kayıtlarla güncellendi; yeni robot özelliği eklenmedi.

## Branch ve hedef

GitHub branch uçları `git ls-remote --heads origin` ile salt okunur doğrulandı:

- Çalışılan branch: `feature/imu-demo-ramp`; mevcut HEAD `4d46bd6`.
- `origin/feature/fsm-maneuvers-tests`: aynı `4d46bd6`; branch'in mevcut tabanı.
- `origin/main`: `1992058`; yerel `main` ise daha eski `ad10f5c`.
- HEAD ile FSM tabanı arasında henüz commit farkı yok; değişiklikler working tree'de.
- `origin/main..HEAD` beş commit içeriyor: kamera katkısı `ec6c070`, kamera/main
  entegrasyonu `6193fec`, FSM entegrasyonu `bc2cdd8`, FSM manevra/testleri `fdedbe7`,
  çalıştırılabilirlik düzeltmesi `4d46bd6`.
- GitHub'da `feature/imu-demo-ramp` adlı remote branch henüz yok; push yapılmadı.

**Şimdiki dar kapsamlı PR hedefi:**
`feature/imu-demo-ramp` → `feature/fsm-maneuvers-tests`.
Böylece yalnızca aşağıdaki yeni commit'ler değerlendirilir. Doğrudan main'e PR
kamera/FSM'nin yukarıdaki beş commit'ini de taşır; bu işi tek başına sunmaz.
FSM tabanı ekip tarafından main'e alındıktan sonra hedef `main` olarak yeniden
incelenebilir. O aşamadaki ancestry/squash farkı kontrol edilmelidir; burada
branch değiştirme, rebase veya merge yapılmadı.

## 1 — FSM mesafe düzeltmesi ve sınır testleri

Önerilen mesaj: `fix(fsm): enter caution at the explore clearance boundary`

Tam liste: [01-fsm.paths](commit-scopes/01-fsm.paths).

- `firescout_fs01/scripts/firescout_fsm.py`
- `firescout_fs01/test/test_fsm_motion_policy.py`
- `firescout_fs01/test/test_fsm_lidar_boundaries.py`

Sorun: CLEAR olan 1.20–1.50 m aralığında EXPLORE seçilirken ileri hareketin
`>1.50 m` koşuluyla kesilmesi. Çözüm mevcut CAUTION durumunu seçmek; mevcut
0.02 m/s politikasını kullanmak. Sensör eşikleri, 0.80 m duruş payı, AVOID ve
eğim/tazelik/tehlike/temas korumaları aynı kalır. Bu commit dünya dosyasını,
geometri testlerini veya kanıt arşivlerini içermez; orijinal tabanda tek başına
test edilebilir.

## 2 — Dünya, 20° rampa ve beş alçak tümsek

Önerilen mesaj: `feat(sim): add separate tilt ramp and low bump demo lane`

Tam liste: [02-world.paths](commit-scopes/02-world.paths).

- `firescout_fs01/worlds/industrial_world.sdf`
- `firescout_fs01/test/test_imu_demo_ramp.py`
- `firescout_fs01/test/test_rough_ground_geometry.py`

Eşleşen görsel/çarpışma geometrisi, yumuşak girişler, robot boyutları, ana yol/
engel boşlukları ve yüzey sürekliliği. Dünya dosyası rampayı ve beşli yolu birlikte
barındırdığı için bu commit'te birlikte tutulur. FSM/sensör kaynakları bu gruba girmez.
Fiziksel geçişin kapsamı sonraki dokümantasyon commit'inde açıklanır; SDF testleri
tek başına sürüş kanıtı değildir.

## 3 — README, test rehberleri ve küçük inceleme kanıtları

Önerilen mesaj: `docs: record verified FSM and terrain tests with limitations`

Tam liste: [03-docs.paths](commit-scopes/03-docs.paths), **31 dosya**:
11 README/rehber/hazırlık dosyası ve 20 seçilmiş kanıt dosyası.

Dokümanlar: ana README, paket README, iki demo rehberi, `VALIDATION_RESULTS.md`,
bu plan ve `docs/commit-scopes/` altındaki üç kapsam listesi/iki envanter.
Seçilmiş mevcut kanıtlar özgün klasörlerinde tutulur; yeni kopyaları oluşturulmaz.
[Dosya boyutları ve SHA256](commit-scopes/small_evidence_manifest.json).
Kanıtların kendisi toplam **0.909 MB**; bütün bu commit yaklaşık 1 MB'dir.

Küçük paketin içeriği:

- FSM yaklaşma grafiği, özeti, olayları ve kayıt kontrolü;
- doğrudan 20° ve düz dönüşün iki görüntüsü ile ölçüm özeti;
- beşli yolun dünya görüntüsü, geometri hesabı ve son güvenlik kontrolü;
- tek/beşli yol grafikleri, özetleri, olayları ve kayıt doğrulama JSON'ları;
- kesilen deneme notu ve tamamlanan beşli denemenin kontrollü ara açıklaması.

Bu paket, 1.498 m'de CAUTION/0.02 m/s, rampada WARNING→SAFE_STOP, ayrı 20°
yerleştirme/NORMAL dönüşü, tek ve beşli tam geçişleri açıklamaya yeterli küçük
inceleme paketidir. Tam rampa tırmanışı veya kesintisiz beşli sürüş iddia edilmez.
Kamera STALE sorunu, LiDAR STALE, kısa IMU UNKNOWN, iki yaşlı poz örneğinin
hariç bırakılması, kayıtta transport kaybı ve kontrollü ara açıkça belirtilir.

Tam yerel RESULTS.md dosyaları, bütün MANIFEST'ler ve çalıştırılmış test
yardımcıları bu küçük seçime dahil edilmedi; bazıları yerel büyük medyaya veya
oturuma özgü PID'lere bağlıdır. Public doküman bağlantıları yalnızca seçilen küçük
kanıtlara gider. Replay için yerel ham arşiv gerekir.

## Büyük medya: otomatik kapsam dışında

MB = 1,000,000 byte. Tam dosya yolları, byte sayıları ve SHA256:
[media_inventory.json](commit-scopes/media_inventory.json).

| Yerel arşiv | Bag | Video |
|---|---:|---:|
| FSM mesafe düzeltmesi / gerçek rampa yaklaşması | 18.78 MB | 3.49 MB |
| Eski rampa denemesi / ayrı doğrudan yerleştirme | 11.15 MB | 3.92 MB |
| Tek alçak tümsek | 6.14 MB | 7.77 MB |
| Kesilen ilk beşli deneme | 6.78 MB | yok |
| Tamamlanan beşli deneme | 26.35 MB | 8.28 MB |

Ayrıca yerelde ignore edilen eski teslim ZIP'i 0.80 MB. ZIP içinde mevcut
repository dosyalarıyla byte eşit 16 girdi, diğer/eski 9 girdi var; tüm arşivin
birebir kopya olduğu iddia edilmiyor. Ayrı bag/video dosyalarında SHA256 eşitliği
bulunmadı; bunlar farklı denemeler. Yine de her denemenin tüm ham medyasını aynı
PR'a koymak gerekli değil.

Takip edilmeyen/ignore edilen bag/video/ZIP toplamı yaklaşık **93.46 MB**.
Daha önce Git'e alınmış IMU bag'i ayrıca 1.81 MB; ona dokunulmaz. Bütün inceleme
medyası toplamı yaklaşık 95.27 MB. Bu dosyaların hiçbiri kapsam listelerinde yok.

Önerilen ek kanıt sırası, ancak ihtiyaç olduğunda ayrıca seçilmek üzere:

1. Görüntülü kısa demo istenirse son beşli videoyu (8.28 MB) seç; bu yalnızca
   60 saniyelik orta bölüm kesitidir, tüm geçiş değildir. Ayrı yayın/teslim eki
   olarak sunulabilir; bu hazırlıkta yükleme/yayın yapılmadı.
2. Grafiği ham CSV'den yeniden üretmek için beşli CSV 5.59 MB, tek CSV 1.03 MB,
   FSM yaklaşma CSV'si 0.77 MB. Bunlar da otomatik kapsamda değil.
3. ROS replay/ham sensör incelemesi gerekirse son beşli 26.35 MB ve FSM düzeltmesi
   18.78 MB bag'leri en yararlı iki ayrı kayıttır; mevcut küçük paket replay yapmaz.
4. Eski başarısız rampa/beşli bag'leri, önceki videolar, ZIP, oturum konsol logları
   ve ilgisiz `three_monitor_integration_*` klasörleri yerelde korunsun.

## Kapsamların kullanımı ve kontroller

Bu dosyalar stage işlemi yapmaz. Daha sonra commit izni verildiğinde, önce index
kontrol edilerek her grup ayrı ayrı `git add --pathspec-from-file=...` ile seçilip
staged diff'i incelenebilir; bir sonraki gruba geçmeden önce o grubun commit'i
ayrı oluşturulur. `git add .`, `git add evidence/` veya `git add -A` bu planın parçası değildir.
Bu hazırlıkta hiçbir `git add`, commit, push veya merge çalıştırılmadı.

Üç kapsamın geçici dizindeki patch önizlemeleri `/tmp/firescout_commit_previews/`
altında hazırlandı; çalışma branch'inin index'ine dokunulmadı.

Bu hazırlıkta gerçekten yapılan kontroller:

- Orijinal HEAD paketine yalnızca 1. patch uygulandı: **93 unittest geçti**.
- Ardından 2. patch uygulandı: **101 unittest geçti**, `gz sdf -k`: **Valid**.
- Ayrı orijinal HEAD paketine yalnızca 2. patch uygulandı: **8 geometri testi geçti**.
- Böylece FSM düzeltmesi rampadan, dünya geometrisi de FSM düzeltmesinden ayrı
  uygulanıp kendi testleriyle denetlendi. Geçici dizinlere büyük bag/video kopyalanmadı.
- Doküman bağlantıları, kapsam listelerinin ayrılığı, küçük kanıt SHA256'ları,
  medya boyutları/yinelenme kontrolü ve `git diff --check` denetlendi.
- Önceki kaynak/test/dünya ve evidence dosyaları içerik hash'leriyle korundu;
  bu hazırlıkta mevcut dosyalardan yalnızca iki README ve iki rehber düzenlendi.
- Index boş; commit, push ve merge yok. Bu kontrol sırasında canlı sürüş yapılmadı.
  Normal workspace derlemesinin daha önceki başarılı kaydı
  `evidence/rough_ground_2026-11-08/build.log` altında yerelde korunur; kaynak kod
  değişmediği için bu dokümantasyon hazırlığında derleme yeniden çalıştırılmadı.
