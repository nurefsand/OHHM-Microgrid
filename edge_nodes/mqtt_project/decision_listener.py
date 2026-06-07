import paho.mqtt.client as mqtt
import json

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "kocaeli_grid/sensors/live_state"

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        print("\n📥 TÜM SİSTEM VERİSİ GELDİ")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print("Hata:", e)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Bağlandı")
        client.subscribe(TOPIC)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_forever()