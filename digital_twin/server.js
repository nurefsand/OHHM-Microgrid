const express = require("express");
const cors = require("cors");
const http = require("http");
const { Server } = require("socket.io");
const mqtt = require("mqtt");
const { InfluxDB, Point } = require("@influxdata/influxdb-client");

// --- 1. SUNUCU VE SOCKET.IO AYARLARI ---
const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const io = new Server(server, { cors: { origin: "*" } });

// --- 2. INFLUXDB V3 AYARLARI ---
// Not: Ege'nin Python kodundaki 8181 portunu kullanıyoruz
const INFLUX_URL = "http://localhost:8086";
const INFLUX_TOKEN = "test";
const INFLUX_ORG = "admin"; // v3 için formalite
const INFLUX_BUCKET = "afet_db";

const writeApi = new InfluxDB({ url: INFLUX_URL, token: INFLUX_TOKEN }).getWriteApi(INFLUX_ORG, INFLUX_BUCKET, 'ms');

// --- 3. MQTT (BERİL'İN SUNUCUSU) AYARLARI ---
const MQTT_BROKER = "mqtt://172.20.10.3:1884";
const mqttClient = mqtt.connect(MQTT_BROKER);

mqttClient.on("connect", () => {
    console.log("[BAŞARILI] Beril'in MQTT ağına bağlanıldı! Veri dinleniyor...");
    mqttClient.subscribe("kocaeli_grid/#");
});

// --- 4. VERİ AKIŞI VE ENTEGRASYON ---
mqttClient.on("message", (topic, message) => {
    try {
        const veri = JSON.parse(message.toString());

        // A) Sensör Verisi (Nazenin'den)
        if (topic === "kocaeli_grid/sensors/live_state") {
            const sebekeGucu = veri.grid_state.total_grid_power_kw;
            console.log(`[SENSÖR] Şebeke Gücü: ${sebekeGucu} kW`);

            // InfluxDB'ye Yaz
            const point = new Point("energy")
                .tag("node", "genel_sebeke")
                .floatField("power_kw", sebekeGucu);
            writeApi.writePoint(point);
            writeApi.flush();

            // Frontend'e (Dashboard'a) Canlı Fırlat
            io.emit("sensor_guncelle", veri.grid_state);
        }

        // B) Karar Motoru Komutları (Nurefşan'dan)
        else if (topic === "kocaeli_grid/commands/relays") {
            console.log("[KARAR] Röle durumları güncellendi:", veri);

            // InfluxDB'ye Yaz
            for (const [node_id, durum] of Object.entries(veri)) {
                const point = new Point("karar_motoru")
                    .tag("node_id", node_id)
                    .intField("durum", durum);
                writeApi.writePoint(point);
            }
            writeApi.flush();

            // Frontend'e (Dashboard'a) Canlı Fırlat
            io.emit("role_guncelle", veri);
        }
    } catch (err) {
        console.error("[HATA] Veri işlenemedi:", err.message);
    }
});

// Geriye dönük sorgular için eski API ucunu koruyoruz
app.get("/api/status", (req, res) => {
    res.json({ status: "Otonom Sistem Aktif" });
});

// Sunucuyu 3000 portunda başlat
// Arayüz (HTML) dosyasını sunucu üzerinden yayınla
app.get("/", (req, res) => {
    res.sendFile(__dirname + "/dashboardd.html");
});
server.listen(5000, () => {
    console.log("Backend ve WebSocket 5000 portunda çalışıyor...");
});