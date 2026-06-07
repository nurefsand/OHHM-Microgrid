import json
import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_STATE = "kocaeli_grid/sensors/live_state"
TOPIC_COMMANDS = "kocaeli_grid/commands/relays"

# Paho MQTT Version 2 uyumlu istemci
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Eylem Katmanı
def on_message(client, userdata, msg):
    try:
        commands = json.loads(msg.payload.decode())
        print(f"\n🧠 [KARAR MOTORU] Komutlar Alındı: {commands}")


        for node_id, action in commands.items():
            status_text = "ENERJİ VERİLDİ (RÖLE KAPALI)" if action == 1 else "ENERJİ KESİLDİ (RÖLE AÇIK)"
            print(f"   ∟ {node_id}: {status_text}")
    except Exception as e:
        print("❌ Komut işleme hatası:", e)


# GÜNCELLEME: 'properties' parametresi eklendi
def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("✅ HiveMQ Bağlantısı Başarılı. Komut kanalı dinleniyor...")
        client.subscribe(TOPIC_COMMANDS)
    else:
        print(f"❌ Bağlantı hatası: {rc}")


client.on_connect = on_connect
client.on_message = on_message


def start_network():
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start()
    except Exception as e:
        print("❌ Broker bağlantı hatası:", e)


def send_snapshot(grid_power_kw, nodes_data):

    packet = {
        "grid_state": {
            "total_grid_power_kw": float(grid_power_kw),
            "total_microgrid_power_kw": 5300.0,
            "total_comm_capacity_mbps": 100.0
        },
        "nodes": nodes_data
    }
    try:
        # ensure_ascii=False ile Türkçe karakterlerin bozulmasını engelliyoruz
        payload = json.dumps(packet, ensure_ascii=False)
        client.publish(TOPIC_STATE, payload, qos=1)
        print(f"📡 [SNAPSHOT] Gönderildi - Şebeke: {grid_power_kw} kW")
    except Exception as e:
        print("❌ Gönderim başarısız:", e)