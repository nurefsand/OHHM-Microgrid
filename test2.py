import paho.mqtt.client as mqtt
import json
import time

MQTT_BROKER = "172.20.10.3"
MQTT_PORT = 1884
TOPIC_SENSOR = "kocaeli_grid/sensors/live_state"
TOPIC_COMMANDS = "kocaeli_grid/commands/relays"

# Senaryo
SCENARIO_FILE = 'senaryo2_haberlesme_cokmus.json'

# --- MQTT CALLBACK FONKSİYONLARI ---
def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print(f"[SİSTEM] ✅ Beril'in ağına bağlanıldı! (Dosya: {SCENARIO_FILE})")
        client.subscribe(TOPIC_COMMANDS)
    else:
        print(f"[SİSTEM] ❌ Bağlantı hatası! Kod: {rc}")

def on_message(client, userdata, msg):
    try:
        komut = msg.payload.decode()
        print(f"\n[SANAL RÖLE] 🧠 Karar Motoru Emir Gönderdi: {komut}")
    except Exception as e:
        print(f"Mesaj okunurken hata: {e}")

# --- ANA AKIŞ ---
# 1. JSON Dosyasını Oku
try:
    with open(SCENARIO_FILE, 'r', encoding='utf-8') as f:
        senaryo_verisi = json.load(f)
    print(f"[DOSYA] 📁 {SCENARIO_FILE} başarıyla yüklendi.")
except FileNotFoundError:
    print(f"[HATA] ❌ {SCENARIO_FILE} bulunamadı! Dosya yolunu kontrol et.")
    exit()

# 2. MQTT İstemcisini Hazırla
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

print(f"[SİSTEM] 📡 {MQTT_BROKER} adresine bağlanılıyor...")

try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
except Exception as e:
    print(f"❌ Bağlantı başarısız: {e}")
    exit()

# 3. Veri Gönderimi
time.sleep(2)
print("\n[SENSÖR] ⚠️ Kritik Durum Algılandı! Senaryo verisi fırlatılıyor...")

# JSON içindeki veriyi aynen gönderiyoruz
client.publish(TOPIC_SENSOR, json.dumps(senaryo_verisi), qos=1)

print("[SENSÖR] 🚀 Veri başarıyla gönderildi. Karar Motoru cevabı için beklemede...")

# Programın kapanmaması için döngü
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n[SİSTEM] 🛑 Program kullanıcı tarafından kapatıldı.")
    client.loop_stop()
    client.disconnect()