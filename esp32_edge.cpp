#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// 1. Ağ ve Broker Ayarları 
const char* ssid = "Beril_Mesh_Agi";       // Beril'in Wi-Fi adı
const char* password = "mesh_password";    // Wi-Fi şifresi
const char* mqtt_broker = "172.20.10.3";
const int mqtt_port = 1884;

// Topic Tanımlamaları
const char* topic_state = "kocaeli_grid/sensors/live_state";
const char* topic_commands = "kocaeli_grid/commands/relays";

// Fiziksel Röle Pin Tanımlamaları 
const int HASTANE_RELE_PIN = 12;
const int AFAD_RELE_PIN = 14;

WiFiClient espClient;
PubSubClient client(espClient);
unsigned long lastMsg = 0;

// --- 2. Karar Motorundan Gelen Komutları Dinleme (Callback) ---
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("\n🧠 [KARAR MOTORU] Komut Geldi [");
  Serial.print(topic);
  Serial.println("] ");

  // Gelen JSON paketini ayrıştır
  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, payload, length);

  if (error) {
    Serial.print("❌ JSON Ayrıştırma Hatası: ");
    Serial.println(error.c_str());
    return;
  }

  // Gelen 1 ve 0 değerlerine göre fiziksel röleleri tetikle
  if (doc.containsKey("NODE_KOU_HASTANE")) {
    int status = doc["NODE_KOU_HASTANE"];
    digitalWrite(HASTANE_RELE_PIN, status == 1 ? HIGH : LOW);
    Serial.printf("   ∟ KOU Hastanesi Rölesi -> %s\n", status == 1 ? "ENERJİ VERİLDİ" : "KESİLDİ");
  }
  if (doc.containsKey("NODE_AFAD_MERKEZ")) {
    int status = doc["NODE_AFAD_MERKEZ"];
    digitalWrite(AFAD_RELE_PIN, status == 1 ? HIGH : LOW);
    Serial.printf("   ∟ AFAD Rölesi -> %s\n", status == 1 ? "ENERJİ VERİLDİ" : "KESİLDİ");
  }
}

// --- 3. Wi-Fi ve MQTT Bağlantı Yönetimi ---
void setup_wifi() {
  delay(10);
  Serial.println("\n[WIFI] Beril'in ağına bağlanılıyor...");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WIFI] ✅ Bağlantı sağlandı!");
  Serial.print("[WIFI] IP Adresi: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("[MQTT] Yerel broker bağlantısı deneniyor...");
    if (client.connect("ESP32_Edge_Node")) {
      Serial.println(" ✅ Başarılı!");
      client.subscribe(topic_commands); 
    } else {
      Serial.print(" ❌ Başarısız, rc=");
      Serial.print(client.state());
      Serial.println(" 5 saniye sonra tekrar denenecek.");
      delay(5000);
    }
  }
}

// --- 4. Bütüncül Sistem Snapshot Paketini Gönderme ---
void sendSystemSnapshot(float grid_power, float hospital_demand) {
 
  JsonDocument doc;

  // Grid State Katmanı
  JsonObject grid_state = doc.createNestedObject("grid_state");
  grid_state["total_grid_power_kw"] = grid_power;
  grid_state["total_microgrid_power_kw"] = 5300.0;
  grid_state["total_comm_capacity_mbps"] = 1000.0;

  // Düğümler Listesi (Nodes Array)
  JsonArray nodes = doc.createNestedArray("nodes");

  // Düğüm 1: KOU Hastanesi (Sensörden gelen p_kw buraya yazılır)
  JsonObject n1 = nodes.createNestedObject();
  n1["node_id"] = "NODE_KOU_HASTANE";
  n1["node_name"] = "KOU Hastanesi";
  n1["location"] = "İzmit TM";
  n1["node_type"] = "Kritik_Saglik";
  JsonObject p1 = n1.createNestedObject("parameters");
  p1["priority_weight"] = 0.93;
  p1["demand_power_kw"] = hospital_demand; 
  p1["min_required_power_kw"] = 2500.0;
  p1["min_service_ratio"] = 0.50;

  // Düğüm 2: AFAD Merkez (Sabit kısıtlı simülasyon düğümü)
  JsonObject n2 = nodes.createNestedObject();
  n2["node_id"] = "NODE_AFAD_MERKEZ";
  n2["node_name"] = "AFAD Kocaeli";
  n2["location"] = "Köseköy TM";
  n2["node_type"] = "Kritik_Koordinasyon";
  JsonObject p2 = n2.createNestedObject("parameters");
  p2["priority_weight"] = 0.87;
  p2["demand_power_kw"] = 210.0;
  p2["min_required_power_kw"] = 160.0;
  p2["min_service_ratio"] = 1.00;

  // Düğüm 3: Gebze OSB (Ertelenebilir Yük)
  JsonObject n3 = nodes.createNestedObject();
  n3["node_id"] = "NODE_OSB_SANAYI";
  n3["node_name"] = "Gebze OSB";
  n3["location"] = "Gebze OSB TM";
  n3["node_type"] = "Ertelenebilir_Yuk";
  JsonObject p3 = n3.createNestedObject("parameters");
  p3["priority_weight"] = 0.52;
  p3["demand_power_kw"] = 4000.0;
  p3["min_required_power_kw"] = 1000.0;
  p3["min_service_ratio"] = 0.25;

  // JSON'ı stringe çevir ve yayınla
  char buffer[2048];
  serializeJson(doc, buffer);
  
  if (client.publish(topic_state, buffer)) {
    Serial.printf("📡 [SNAPSHOT SENT] Şebeke: %.1f kW | Hastane Talep: %.1f kW\n", grid_power, hospital_demand);
  } else {
    Serial.println("❌ Paket gönderilemedi! Buffer boyutu yetersiz olabilir.");
  }
}

// --- 5. ANA AYARLAR VE DÖNGÜ ---
void setup() {
  Serial.begin(115200);
  
  // Röle pinlerini çıkış olarak ayarla
  pinMode(HASTANE_RELE_PIN, OUTPUT);
  pinMode(AFAD_RELE_PIN, OUTPUT);
  digitalWrite(HASTANE_RELE_PIN, LOW);
  digitalWrite(AFAD_RELE_PIN, LOW);

  setup_wifi();
  client.setServer(mqtt_broker, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop(); 

  unsigned long now = millis();
  static int step_counter = 0;

  // Her 5 saniyede bir merkeze snapshot fırlat 
  if (now - lastMsg > 5000) {
    lastMsg = now;
    step_counter++;

    // Senaryo Simülasyonu: 6. adımdan sonra şebeke çöker (0.0 kW olur)
    float current_grid_power = (step_counter <= 6) ? 10000.0 : 0.0;
    
    // Sensörden okuduğunu varsaydığın dinamik yük (ADC okuması simülasyonu)
    float simulated_hospital_sensor = 4800.0 + random(-100, 100); 

    if (current_grid_power == 0.0) {
      Serial.println("\n⚠️ [SENSÖR] ROCOF/Voltaj Hatası Algılandı! Şebeke Ayrılıyor...");
    }

    sendSystemSnapshot(current_grid_power, simulated_hospital_sensor);
  }
}