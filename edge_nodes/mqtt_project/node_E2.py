import paho.mqtt.client as mqtt
import json
import time

node_id = "E2"

client = mqtt.Client()
client.connect("localhost", 1883, 60)

while True:
    data = {
        "node_id": node_id,
        "voltage": 580,
        "frequency": 49.5,
        "current": 10,
        "status": "NORMAL",
        "target": ["C1","C2"],
        "hop": 0
    }

    client.publish("grid/nodes", json.dumps(data))
    print("E2 gönderdi:", data)

    time.sleep(2)