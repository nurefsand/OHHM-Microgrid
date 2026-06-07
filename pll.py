import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time


class EnhancedPLL:
    def __init__(self):
        # Kontrol Parametreleri
        self.kp = 0.12
        self.ki = 0.04
        self.dt = 0.01

        # Durumlar
        self.theta_grid = 0.0
        self.theta_inv = 0.0
        self.inv_freq = 46.0  # Başlangıçta düşük frekans
        self.integral = 0.0
        self.error = 0.0
        self.lock_timer = 0
        self.is_locked = False

        # Grafik Veri Havuzları
        self.history_size = 60
        self.time_data = np.arange(self.history_size)
        self.grid_sine = [0] * self.history_size
        self.inv_sine = [0] * self.history_size
        self.error_data = [0] * self.history_size
        self.freq_data = [0] * self.history_size
        self.integral_data = [0] * self.history_size  # PI içsel verisi

    def step(self):
        # 1. Faz Dedektörü (Phase Detector)
        self.error = np.sin(self.theta_grid - self.theta_inv)

        # 2. Döngü Filtresi (Loop Filter / PI)
        self.integral += self.error * self.dt
        df = (self.kp * self.error) + (self.ki * self.integral)
        self.inv_freq = 50.0 + df

        # 3. VCO (Açı Güncelleme)
        self.theta_grid += 2 * np.pi * 50.0 * self.dt
        self.theta_inv += 2 * np.pi * self.inv_freq * self.dt

        # 4. Kilitlenme Mantığı (500ms Kararlılık)
        if abs(self.error) < 0.05:
            self.lock_timer = min(self.lock_timer + 10, 500)
        else:
            self.lock_timer = 0
            self.is_locked = False

        if self.lock_timer >= 500:
            self.is_locked = True  # ATS Rölesi Kapatılabilir

        # Veri Güncelleme
        self.grid_sine.append(np.sin(self.theta_grid))
        self.inv_sine.append(np.sin(self.theta_inv))
        self.error_data.append(self.error)
        self.freq_data.append(self.inv_freq)
        self.integral_data.append(self.integral)

        for data in [self.grid_sine, self.inv_sine, self.error_data, self.freq_data, self.integral_data]:
            data.pop(0)


# --- Görselleştirme Ayarları ---
plt.style.use('dark_background')
fig = plt.figure(figsize=(14, 8))
fig.suptitle('ΩHHM - Otonom Mikroşebeke PLL Senkronizasyon Dashboard', fontsize=18, fontweight='bold', color='#fbbf24')

ax1 = plt.subplot2grid((3, 2), (0, 0), colspan=2)  # Dalga Formu
ax2 = plt.subplot2grid((3, 2), (1, 0))  # Faz Hatası
ax3 = plt.subplot2grid((3, 2), (1, 1))  # Frekans Takibi
ax4 = plt.subplot2grid((3, 2), (2, 0))  # PI İntegral Etkisi
ax5 = plt.subplot2grid((3, 2), (2, 1))  # Durum Paneli (Metin)

pll = EnhancedPLL()


def animate(i):
    pll.step()

    # 1. Dalga Formu (Canlı Senkronizasyon)
    ax1.clear()
    ax1.plot(pll.grid_sine, label='SEDAŞ Şebekesi (Ref)', color='#fbbf24', lw=3)
    ax1.plot(pll.inv_sine, label='İnverter Çıkışı (VCO)', color='#3b82f6', lw=3, ls='--')
    ax1.set_title("Gerçek Zamanlı Sinüs Dalga Çakıştırma", color='#94a3b8')
    ax1.set_ylim(-1.2, 1.2)
    ax1.legend(loc='upper right')
    ax1.grid(alpha=0.2)

    # 2. Faz Hatası (Δθ)
    ax2.clear()
    ax2.fill_between(range(60), pll.error_data, color='#ef4444', alpha=0.3)
    ax2.plot(pll.error_data, color='#ef4444', lw=2)
    ax2.set_title("Faz Hatası (Sıfıra İndirgeniyor)", size=10)
    ax2.set_ylim(-1, 1)

    # 3. Frekans Takibi (Hz)
    ax3.clear()
    ax3.plot(pll.freq_data, color='#4ade80', lw=2)
    ax3.axhline(50, color='white', ls=':', alpha=0.5)
    ax3.set_title("İnverter Frekans Adaptasyonu (Hz)", size=10)
    ax3.set_ylim(44, 56)

    # 4. PI İntegral Çabası
    ax4.clear()
    ax4.plot(pll.integral_data, color='#a855f7', lw=2)
    ax4.set_title("PI Kontrolcü İntegral Akümülasyonu", size=10)

    # 5. Durum Paneli
    ax5.clear()
    ax5.axis('off')
    status_color = '#22c55e' if pll.is_locked else '#f59e0b'
    status_text = "SİSTEM KİLİTLENDİ\n(ATS GÜVENLİ)" if pll.is_locked else "SENKRONİZASYON\nBEKLENİYOR..."

    ax5.text(0.5, 0.7, status_text, ha='center', va='center', fontsize=16, fontweight='bold', color=status_color)
    ax5.text(0.5, 0.3, f"Kararlılık: {int(pll.lock_timer / 5)}%\nHata: {pll.error:.4f}\nFrekans: {pll.inv_freq:.2f} Hz",
             ha='center', va='center', fontsize=12, color='#94a3b8')


ani = FuncAnimation(fig, animate, interval=50)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.show()