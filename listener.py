import json
import paho.mqtt.client as mqtt
from influx_writer import write_node_status

BROKER = "broker.hivemq.com"  # HiveMQ üzerinden dinlemek için ortak broker
PORT = 1883
TOPIC = "kocaeli_grid/sensors/live_state"


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        grid_power = payload["grid_state"]["total_grid_power_kw"]

        # Büyük paketi açıp içindeki her bir düğümü InfluxDB'ye ayrı ayrı yazıyoruz
        for node in payload["nodes"]:
            write_node_status(
                node_id=node["node_id"],
                demand_power=node["parameters"]["demand_power_kw"],
                min_power=node["parameters"]["min_required_power_kw"],
                status=node["parameters"]["status"],
                grid_power=grid_power
            )
        print(f"📥 [DB SUCCESS] {len(payload['nodes'])} düğüm veritabanına işlendi.")

    except Exception as e:
        print("❌ Veri ayrıştırma veya DB hatası:", e)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.subscribe(TOPIC)

print("🎧 Listener (Snapshot Modunda) çalışıyor...")
client.loop_forever()