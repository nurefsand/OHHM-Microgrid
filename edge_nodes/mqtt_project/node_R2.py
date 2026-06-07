import paho.mqtt.client as mqtt
import json

node_id = "R2"

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    status = data.get("parameters", {}).get("status", "UNKNOWN")
    print(node_id, "status:", status)

    print(node_id, "aldı:", data)

    hop = data.get("hop", 0)
    if hop > 5:
        return

    data["hop"] = hop + 1

    targets = data.get("target", [])

    if isinstance(targets, list):
        for t in targets:
            if t == "C1":
                print(node_id, "→ C1'e gönderiyor")
                client.publish("grid/C1", json.dumps(data))

            elif t == "C2":
                print(node_id, "→ C2'ye gönderiyor")
                client.publish("grid/C2", json.dumps(data))

client = mqtt.Client()
client.connect("localhost", 1883, 60)

client.subscribe("grid/nodes")

client.on_message = on_message

client.loop_forever()