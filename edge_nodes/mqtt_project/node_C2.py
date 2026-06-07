import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    print("C2 ALDI:", msg.payload.decode())

client = mqtt.Client()
client.connect("localhost", 1883, 60)

client.subscribe("grid/C2")

client.on_message = on_message

client.loop_forever()