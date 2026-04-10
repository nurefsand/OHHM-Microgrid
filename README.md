# ΩHHM (Otonom Hibrit Haberleşme & Mikroşebeke) ⚡📡

Bu depo, afet durumlarında ana şebekenin (grid) çökmesi senaryosuna karşı geliştirilen **Otonom Hibrit Haberleşme ve Mikroşebeke (ΩHHM)** projesinin kaynak kodlarını, donanım simülasyonlarını ve optimizasyon modellerini içermektedir.

## 🚀 Proje Hakkında
ΩHHM, kısıtlı enerji altında vereceği otonom kararları İzmit-Derince bölgesi pilot topolojisi üzerinde uygulayan, Olay Güdümlü (Event-Driven) bir IoT mimarisidir. Sistem; Fotovoltaik (PV) enerji hasadı, V2G (Vehicle-to-Grid) entegrasyonu ve MILP (Karma Tam Sayılı Doğrusal Programlama) optimizasyon algoritmalarını birleştirerek kritik yüklerin otonom bir şekilde enerjilendirilmesini sağlar.

Optimizasyon temel amaç fonksiyonu: $\max Z = \sum w_i z_i$ (AHP ile belirlenmiş kritiklik ağırlıklarının maksimizasyonu).

## 🧠 Sistem Mimarisi (Sensör -> Edge -> Karar -> Komut)
1. **Veri Toplama:** Edge cihazlar üzerinden okunan SoC ve yük verileri MQTT protokolü ile merkeze iletilir.
2. **Haberleşme:** LoRa/RF tabanlı Mesh ağı, afet anında kendi kendini onararak (self-healing) veri kayıplarını önler.
3. **Karar Motoru:** Uyku modundaki (Islanding) karar motoru uyanır, AHP ve MILP kısıtlarına göre otonom enerji dağıtım kararlarını milisaniyeler içinde alır.
4. **Dijital İkiz:** Tüm sistem InfluxDB zaman serisi veritabanına kaydedilir ve Grafana üzerinden canlı olarak izlenir.
5. **Güç Elektroniği:** ATS (Otomatik Transfer Şalteri) ve V2G donanım bileşenleri MCU üzerinden tetiklenerek fiziksel güç aktarımını gerçekleştirir.

## ⚙️ Kullanılan Teknolojiler
* **Yazılım & Algoritma:** Python, C/C++ (Edge)
* **IoT & Haberleşme:** Eclipse Mosquitto (MQTT), LoRa/RF Mesh
* **Veritabanı & İzleme:** InfluxDB, Grafana
* **Donanım & Simülasyon:** Proteus, Altium Designer
* **Optimizasyon:** MILP, AHP, TOPSIS (MS Excel)

## 👥 Geliştirici Ekibi
Bu proje, Bilgisayar (CE), Elektrik-Elektronik (EE) ve Endüstri (IE) Mühendisliği disiplinlerinin Çevik (Agile) metodoloji etrafında birleşmesiyle geliştirilmektedir.
* **CE Ekibi:** Nurefşan Dolaş, Beril Şener, Nazenin Nur Avcıküçük, Ege Yıldız
* **EE Ekibi:** Mehmet Erkam Güven, Furkan Pancar
* **IE Ekibi:** Fatma Nur Yaşar, Gizem Dinçer
