def on_message(client, userdata, msg):
    try:
        raw = msg.payload.decode()
        print("RAW GELEN:", raw)

        data = json.loads(raw)

        if "node" in data and "power" in data:
            point = (
                Point("sensor_data")
                .tag("node", data["node"])
                .field("power", float(data["power"]))
            )

            write_api.write(bucket=INFLUX_BUCKET, record=point)

        else:
            print("Eksik veri:", data)

    except Exception as e:
        print("JSON HATASI:", msg.payload.decode())