Beşli geçiş sırasında kontrollü ara

Terminale bağlı ilk üst gözetici SIGTERM ile sonlandı. Asıl ROS ölçüm süreci ve Gazebo poz okuyucusu çalışmayı sürdürdü. Hareket bağımsız `ros2 param set /firescout_fsm motion_enabled false` komutuyla kapatıldı; mevcut süreçler incelendi. Yeni monitor veya ikinci kayıt süreci açılmadı. Aynı ölçüm sürecine terminalden bağımsız, SIGTERM temizliği bulunan gözetici bağlandı ve `motion_enabled true` ile aynı fiziksel denemeye devam edildi.

Kayıtta x≈−1.745369 m ve hız sıfır olan sabit bölüm yaklaşık t=250.82…325.91 s. Bu gözlenen sabit poz aralığıdır; parametre komutlarının tam zaman damgası değildir. Bu arayı kamera STALE veya eski 1.50 m FSM uyumsuzluğu sayma. CSV `motion_enabled` sütunu kayıt betiğinin kendi son isteğini tutar; dışarıdan verilen kapatma sırasında true görünmeye devam eder. Gerçek /cmd_vel kaydı bu arada sıfırdır.

Yaklaşma yerleştirmesi ile son düz zemine dönüş dışında robot pozu değiştirilmedi; geçiş boyunca yalnızca FSM /cmd_vel yayımladı. Sonuç, kontrollü ara içeren beş tümseğin tam tekerlekli geçişidir; kesintisiz otonom sürüş olarak sunulmaz. Kamera STALE geçiş sayımları tüm sürüş evresine aittir ve bu kontrollü arayı da kapsayabilir.
