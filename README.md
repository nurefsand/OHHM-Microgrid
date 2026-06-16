# ΩHHM (Otonom Hibrit Haberleşme & Mikroşebeke) ⚡📡

Bu depo, afet durumlarında ana şebekenin (grid) çökmesi senaryosuna karşı geliştirilen **Otonom Hibrit Haberleşme ve Mikroşebeke (ΩHHM)** projesinin kaynak kodlarını, donanım simülasyonlarını ve optimizasyon modellerini içermektedir.

### 🚀 Proje Hakkında
ΩHHM, kısıtlı enerji altında vereceği otonom kararları İzmit-Derince bölgesi pilot topolojisi üzerinde uygulayan, olay güdümlü (event-driven) bir IoT ve otonom yönetim mimarisidir. Sistem; Fotovoltaik (PV) enerji hasadı, V2G (Vehicle-to-Grid) elektrikli araç entegrasyonu ve MILP (Karmaşık Tam Sayılı Doğrusal Programlama) optimizasyon algoritmalarını birleştirerek, afet anında kritik yüklerin (Hastane, AFAD vb.) insan müdahalesi olmadan otonom bir şekilde enerjilendirilmesini sağlar.

Optimizasyon temel amaç fonksiyonu: 
$\max Z = \sum w_i \cdot z_i$ (AHP ile belirlenmiş kritiklik ağırlıklarının maksimizasyonu).

### 🧠 Sistem Mimarisi (Sensör -> Edge -> Karar -> Komut)
* **Veri Toplama (Edge):** Çoklu iş parçacıklı (multithreaded) uç cihaz emülatörleri üzerinden okunan kapasite ve yük verileri MQTT protokolü ile ağa iletilir. Veriler sisteme girmeden önce 0.0 ms hızında çalışan geçerlilik filtresinden (validation) geçer.
* **Çevrimdışı Haberleşme:** İnternet ve GSM çöktüğünde dahi çalışan yerel Eclipse Mosquitto MQTT ağı, kendi kendini onararak (self-healing) veri kayıplarını önler.
* **MILP Otonom Karar Motoru:** PuLP tabanlı karar motoru sahadan gelen anlık verileri işler. C++ tabanlı CBC çözücüsü ile sistem kısıtlarını hesaplayarak, otonom enerji dağıtım şalter kararlarını (u, z) ortalama 71.0 ms içinde alır.
* **Gerçek Zamanlı Dijital İkiz:** Tüm sistem InfluxDB zaman serisi veri tabanına kaydedilir. Node.js Express ve Socket.io (WebSocket) üzerinden beslenen özel Dashboard arayüzü ile güç akışları gecikmesiz ve sayfa yenilenmeden canlı olarak izlenir.
* **Güç Elektroniği:** V2G destekli Çift Aktif Köprü (DAB) ve ATS (Otomatik Transfer Şalteri) röleleri, MCU üzerinden tetiklenerek fiziksel güç aktarımını %1.74 THD gibi yüksek bir güç kalitesiyle gerçekleştirir.

### 📊 Kanıtlanmış Performans Çıktıları
Sistem 5 farklı ekstrem afet senaryosu (S1-S5) altında stres testine tabi tutulmuş ve şu resmi değerler ölçülmüştür:
* **Gerçek Zamanlı Karar Hızı:** Endüstri standardı olan 2000 ms sınırının çok altına inilerek, optimizasyon modeli ortalama **71.0 ms** hızında otonom şalter kararları üretmiştir.
* **Ada Moduna (Islanding) Geçiş:** Ana şebeke koptuğunda (0 kW) sistemin ada moduna geçip kritik yükleri besleme süresi **94.5 ms** olarak ölçülmüştür.
* **Hata Koruması:** Bozuk/eksik veri geldiğinde karar motorunun çökmesini engelleyen validasyon sistemi, hatalı pakedi **0.0 ms**'de reddederek sistemi otonom olarak korumuştur.
* **Kritik Yük Sürekliliği:** Enerji kıtlığı senaryolarında, hastane ve AFAD gibi %100 öncelikli tesislerin enerji sürekliliği tam olarak sağlanmıştır.

### ⚙️ Kullanılan Teknolojiler
* **Yazılım & Otonom Karar:** Python (PuLP), C/C++ (CBC Solver)
* **IoT & Haberleşme:** Eclipse Mosquitto (MQTT), Çevrimdışı Mesh Ağı
* **Backend & İzleme:** Node.js (Express), Socket.io, InfluxDB, HTML/JS
* **Donanım & Güç Elektroniği:** MATLAB/Simulink, Proteus, TI C2000 MCU, SiC MOSFET
* **Optimizasyon & Analiz:** MILP, AHP, TOPSIS

### 👥 Geliştirici Ekibi
Bu proje, Bilgisayar (CE), Elektrik-Elektronik (EE) ve Endüstri (IE) Mühendisliği disiplinlerinin Çevik (Agile) metodoloji etrafında birleşmesiyle geliştirilmiştir.
* **CE Ekibi:** Nurefşan Dolaş, Beril Şener, Nazenin Nur Avcıküçük, Ege Yıldız
* **EE Ekibi:** Mehmet Erkam Güven, Furkan Pancar
* **IE Ekibi:** Fatma Nur Yaşar
