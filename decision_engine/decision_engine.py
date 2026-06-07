"""
ΩHHM - Otonom Hibrit Haberleşme & Mikroşebeke Karar Motoru (Decision Engine) - Ana Döngü İskeleti
"""

import json
import time
import logging
from dataclasses import dataclass
from typing import Optional
import paho.mqtt.client as mqtt

# PuLP — MILP çözücü (pip3 install pulp)
from pulp import (
    LpProblem, LpMaximize, LpVariable, LpBinary,
    lpSum, value, PULP_CBC_CMD
)

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("DecisionEngine")


# 1. VERİ YAPILARI (JSON Sözleşmesiyle Birebir Eşleşir)

@dataclass
class GridState:
    """Genel şebeke durumu — sensörlerden veya InfluxDB'den anlık okunur."""
    total_grid_power_kw: float        # E^grid  — şebekeden kalan toplam güç
    total_microgrid_power_kw: float   # E^mg    — PV + V2G toplam kapasitesi
    total_comm_capacity_mbps: float   # C^tot   — Mesh ağı toplam bant genişliği


@dataclass
class NodeParameters:
    """Bir tesisin statik kısıt parametreleri. AHP katsayıları (w_i) ve min/max enerji sınırları burada saklanır."""
    priority_weight: float           # w_i   — TOPSIS kritiklik skoru
    demand_power_kw: float           # D_i   — tam kapasite enerji talebi
    min_required_power_kw: float     # L_i   — hayati minimum enerji (kırmızı çizgi)
    max_acceptable_power_kw: float   # U_i   — üst enerji limiti
    max_v2g_support_kw: float        # V_max_i — V2G'den alınabilecek max destek
    min_service_ratio: float         # r_i   — min hizmet seviyesi (0.0–1.0)
    initial_reliability_score: float # a_i   — altyapı sağlamlık skoru
    demand_comm_mbps: float          # Q_i   — haberleşme talebi
    min_required_comm_mbps: float    # M_i   — min haberleşme eşiği
    outage_risk_level: str           # "düşük" / "orta" / "yüksek"
    recovery_time_hrs: float         # tahmini toparlanma süresi


@dataclass
class Node:
    """Bir kritik tesis (düğüm) nesnesi."""
    node_id: str
    node_name: str
    location: str
    node_type: str
    parameters: NodeParameters


@dataclass
class DecisionOutput:
    """Karar Motoru'nun bir düğüm için ürettiği çıktılar.
    Donanım katmanına (Erkam & Furkan) ve InfluxDB'ye (Ege) iletilir."""
    node_id: str
    allocated_grid_power_kw: float = 0.0       # x_i
    allocated_mg_power_kw: float = 0.0         # v_i
    allocated_comm_capacity_mbps: float = 0.0  # c_i
    unmet_energy_deficit_kw: float = 0.0       # e_i
    unmet_comm_deficit_mbps: float = 0.0       # h_i
    service_level_ratio: float = 0.0           # z_i  (0.0–1.0)
    activation_status: int = 0                 # u_i  (1=ATS kapat, 0=izole et)

# 2. JSON VERİ YÜKLEYİCİ

def load_system_state(json_path: str) -> tuple[GridState, list[Node]]:
    """JSON veri sözleşmesinden grid_state ve nodes listesini yükler."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    gs = data["grid_state"]
    grid = GridState(
        total_grid_power_kw=gs["total_grid_power_kw"],
        total_microgrid_power_kw=gs["total_microgrid_power_kw"],
        total_comm_capacity_mbps=gs["total_comm_capacity_mbps"],
    )

    nodes = []
    for n in data["nodes"]:
        p = n["parameters"]
        nodes.append(Node(
            node_id=n["node_id"],
            node_name=n["node_name"],
            location=n["location"],
            node_type=n["node_type"],
            parameters=NodeParameters(
                priority_weight=p["priority_weight"],
                demand_power_kw=p["demand_power_kw"],
                min_required_power_kw=p["min_required_power_kw"],
                max_acceptable_power_kw=p["max_acceptable_power_kw"],
                max_v2g_support_kw=p["max_v2g_support_kw"],
                min_service_ratio=p["min_service_ratio"],
                initial_reliability_score=p["initial_reliability_score"],
                demand_comm_mbps=p["demand_comm_mbps"],
                min_required_comm_mbps=p["min_required_comm_mbps"],
                outage_risk_level=p["outage_risk_level"],
                recovery_time_hrs=p["recovery_time_hrs"],
            )
        ))

    return grid, nodes


# 3. KURAL MOTORU (Rule Engine)

ALPHA = 1.0
BETA  = 1.0


def compute_objective(outputs: list[DecisionOutput], nodes: list[Node]) -> float:
    """Amaç fonksiyonu: Σ w_i * z_i - α * e_i - β * h_i"""
    total = 0.0
    node_map = {n.node_id: n for n in nodes}
    for out in outputs:
        w_i = node_map[out.node_id].parameters.priority_weight
        total += w_i * out.service_level_ratio
        total -= ALPHA * out.unmet_energy_deficit_kw
        total -= BETA  * out.unmet_comm_deficit_mbps
    return total


class RuleEngine:
    """Greedy kural motoru — MILPSolver'a geçilene kadar yedek olarak çalışır."""

    def __init__(self, alpha: float = ALPHA, beta: float = BETA):
        self.alpha = alpha
        self.beta  = beta

    def _priority_sort(self, nodes: list[Node]) -> list[Node]:
        return sorted(nodes, key=lambda n: n.parameters.priority_weight, reverse=True)

    def _allocate_energy(self, node, remaining_grid, remaining_mg):
        p = node.parameters
        grid_alloc = max(min(p.demand_power_kw, p.max_acceptable_power_kw, remaining_grid), 0.0)
        mg_alloc   = max(min(max(p.demand_power_kw - grid_alloc, 0.0), p.max_v2g_support_kw, remaining_mg), 0.0)
        total      = grid_alloc + mg_alloc
        z_i        = min(total / p.demand_power_kw, 1.0) if p.demand_power_kw > 0 else 0.0
        e_i        = max(p.demand_power_kw - total, 0.0)
        return grid_alloc, mg_alloc, e_i, z_i

    def _allocate_comm(self, node, remaining_comm):
        p   = node.parameters
        c_i = max(min(p.demand_comm_mbps, remaining_comm), 0.0)
        h_i = max(p.demand_comm_mbps - c_i, 0.0)
        return c_i, h_i

    def _decide_activation(self, node, z_i):
        p = node.parameters
        if z_i >= p.min_service_ratio:
            return 1
        if z_i * p.demand_power_kw >= p.min_required_power_kw * 0.8:
            log.warning(f"[{node.node_id}] Yumuşatılmış eşikle aktif (z={z_i:.2f})")
            return 1
        return 0

    def run(self, grid: GridState, nodes: list[Node]) -> list[DecisionOutput]:
        outputs        = []
        remaining_grid = grid.total_grid_power_kw
        remaining_mg   = grid.total_microgrid_power_kw
        remaining_comm = grid.total_comm_capacity_mbps

        for node in self._priority_sort(nodes):
            log.info(f"İşleniyor: {node.node_name} (w={node.parameters.priority_weight})")
            x_i, v_i, e_i, z_i = self._allocate_energy(node, remaining_grid, remaining_mg)
            c_i, h_i            = self._allocate_comm(node, remaining_comm)
            u_i                 = self._decide_activation(node, z_i)
            remaining_grid -= x_i
            remaining_mg   -= v_i
            remaining_comm -= c_i
            outputs.append(DecisionOutput(
                node_id=node.node_id,
                allocated_grid_power_kw=round(x_i, 2),
                allocated_mg_power_kw=round(v_i, 2),
                allocated_comm_capacity_mbps=round(c_i, 2),
                unmet_energy_deficit_kw=round(e_i, 2),
                unmet_comm_deficit_mbps=round(h_i, 2),
                service_level_ratio=round(z_i, 4),
                activation_status=u_i,
            ))
            log.info(f"  → Şebeke: {x_i:.0f}kW | V2G: {v_i:.0f}kW | Hab: {c_i:.0f}Mbps | z={z_i:.2f} | u={u_i}")

        return outputs


# 4. MILP SOLVER — PuLP Entegrasyonu

class MILPSolver:
    """
    PuLP ile tam MILP optimizasyonu.

    Amaç fonksiyonu (Fatma Nur):
        max Σ w_i * z_i - α * Σ e_i - β * Σ h_i

    Kısıtlar:
        Σ x_i             <= E^grid
        Σ v_i             <= E^mg
        Σ c_i             <= C^tot
        x_i + v_i         >= L_i * r_i * 0.8 * u_i   (yumuşatılmış min hizmet)
        x_i + v_i         <= U_i * u_i
        v_i               <= V_max_i
        z_i * D_i          = x_i + v_i
        u_i               in {0, 1}

    AHP/TOPSIS katsayıları (Gizem Dinçer):
        KOU Hastane    : 0.91
        Gebze Hastane  : 0.88 (*geçici)
        112 Acil       : 0.86 (*geçici)
        AFAD           : 0.84
        Baz İstasyonu  : 0.72
        Su Pompası     : 0.63
    """

    def __init__(self, alpha: float = ALPHA, beta: float = BETA):
        self.alpha = alpha
        self.beta  = beta

    def run(self, grid: GridState, nodes: list[Node]) -> list[DecisionOutput]:
        prob = LpProblem("OHHM_Afet_Enerjisi", LpMaximize)

        ids = [n.node_id for n in nodes]
        p   = {n.node_id: n.parameters for n in nodes}

        # --- Karar değişkenleri ---
        x = {i: LpVariable(f"x_{i}", lowBound=0) for i in ids}  # şebeke enerjisi
        v = {i: LpVariable(f"v_{i}", lowBound=0) for i in ids}  # V2G enerjisi
        c = {i: LpVariable(f"c_{i}", lowBound=0) for i in ids}  # haberleşme
        z = {i: LpVariable(f"z_{i}", lowBound=0, upBound=1) for i in ids}  # hizmet seviyesi
        e = {i: LpVariable(f"e_{i}", lowBound=0) for i in ids}  # enerji açığı
        h = {i: LpVariable(f"h_{i}", lowBound=0) for i in ids}  # haberleşme açığı
        u = {i: LpVariable(f"u_{i}", cat=LpBinary) for i in ids}  # röle kararı

        # --- Amaç fonksiyonu ---
        prob += lpSum(
            p[i].priority_weight * z[i] - self.alpha * e[i] - self.beta * h[i]
            for i in ids
        )

        # --- Kapasite kısıtları ---
        prob += lpSum(x[i] for i in ids) <= grid.total_grid_power_kw,       "Sebeke_Kap"
        prob += lpSum(v[i] for i in ids) <= grid.total_microgrid_power_kw,  "MG_Kap"
        prob += lpSum(c[i] for i in ids) <= grid.total_comm_capacity_mbps,  "Hab_Kap"

        # --- Düğüm bazlı kısıtlar ---
        for i in ids:
            pi = p[i]
            prob += v[i] <= pi.max_v2g_support_kw,                                              f"V2G_lim_{i}"
            prob += x[i] + v[i] <= pi.max_acceptable_power_kw * u[i],                          f"Ust_lim_{i}"
            prob += x[i] + v[i] >= pi.min_required_power_kw * pi.min_service_ratio * 0.8 * u[i], f"Min_hiz_{i}"
            prob += c[i] <= pi.demand_comm_mbps * u[i],                                         f"Hab_lim_{i}"
            prob += z[i] * pi.demand_power_kw == x[i] + v[i],                                  f"Hiz_def_{i}"
            prob += e[i] >= pi.demand_power_kw - (x[i] + v[i]),                                f"Enj_acik_{i}"
            prob += h[i] >= pi.demand_comm_mbps - c[i],                                         f"Hab_acik_{i}"

        # --- Çöz ---
        prob.solve(PULP_CBC_CMD(msg=0))
        log.info(f"MILP durum: {prob.status} | Amaç: {value(prob.objective):.4f}")

        # --- Sonuçları DecisionOutput'a dönüştür ---
        outputs = []
        for node in nodes:
            i   = node.node_id
            x_i = round(value(x[i]) or 0.0, 2)
            v_i = round(value(v[i]) or 0.0, 2)
            c_i = round(value(c[i]) or 0.0, 2)
            e_i = round(value(e[i]) or 0.0, 2)
            h_i = round(value(h[i]) or 0.0, 2)
            z_i = round(value(z[i]) or 0.0, 4)
            u_i = int(round(value(u[i]) or 0.0))
            log.info(f"  [{i}] Şebeke:{x_i}kW | V2G:{v_i}kW | Hab:{c_i}Mbps | z={z_i:.2f} | u={u_i}")
            outputs.append(DecisionOutput(
                node_id=i,
                allocated_grid_power_kw=x_i,
                allocated_mg_power_kw=v_i,
                allocated_comm_capacity_mbps=c_i,
                unmet_energy_deficit_kw=e_i,
                unmet_comm_deficit_mbps=h_i,
                service_level_ratio=z_i,
                activation_status=u_i,
            ))

        return outputs

# 5. EVENT-DRIVEN ANA DÖNGÜ

class DecisionEngine:
    """Olay güdümlü (Event-Driven) Karar Motoru ana sınıfı."""

    def __init__(self, use_milp: bool = False):
        self.solver       = MILPSolver() if use_milp else RuleEngine()
        self.is_islanding = False
        self.last_outputs: list[DecisionOutput] = []

    def on_islanding_detected(self, grid: GridState, nodes: list[Node]) -> list[DecisionOutput]:
        log.warning("!!! ISLANDING DETECTED — Ada modu aktif !!!")
        self.is_islanding = True
        # Başına 'return' ekleyerek çıkan sonuçları MQTT katmanına teslim ediyoruz.
        return self.run(grid, nodes)

    def on_grid_restored(self) -> None:
        log.info("Şebeke geri geldi. Normal moda dönülüyor.")
        self.is_islanding = False

    def run(self, grid: GridState, nodes: list[Node]) -> list[DecisionOutput]:
        t_start = time.time()
        log.info("=" * 60)
        log.info("Karar Motoru başlatıldı.")
        log.info(f"Kapasite → Şebeke: {grid.total_grid_power_kw}kW | MG: {grid.total_microgrid_power_kw}kW | Haberleşme: {grid.total_comm_capacity_mbps}Mbps")

        outputs = self.solver.run(grid, nodes)
        obj_val = compute_objective(outputs, nodes)
        elapsed = time.time() - t_start

        log.info(f"Amaç fonksiyonu değeri: {obj_val:.4f}")
        log.info(f"Karar süresi: {elapsed*1000:.1f}ms")
        if elapsed > 2.0:
            log.error(f"KRİTİK: Hedef 2s gecikme aşıldı! ({elapsed:.2f}s)")

        self.last_outputs = outputs
        self._dispatch_relay_commands(outputs)
        log.info("=" * 60)
        return outputs

    def _dispatch_relay_commands(self, outputs: list[DecisionOutput]) -> None:
        log.info("--- RÖLE KOMUTLARI ---")
        for out in outputs:
            status = "AKTİF ✓" if out.activation_status == 1 else "İZOLE ✗"
            log.info(f"  {out.node_id:<25} → {status} | z={out.service_level_ratio:.2f} | Enerji açığı: {out.unmet_energy_deficit_kw:.0f}kW")

    def get_outputs_as_json(self) -> str:
        result = []
        for out in self.last_outputs:
            result.append({
                "node_id": out.node_id,
                "decision_outputs": {
                    "allocated_grid_power_kw":      out.allocated_grid_power_kw,
                    "allocated_mg_power_kw":        out.allocated_mg_power_kw,
                    "allocated_comm_capacity_mbps": out.allocated_comm_capacity_mbps,
                    "unmet_energy_deficit_kw":      out.unmet_energy_deficit_kw,
                    "unmet_comm_deficit_mbps":      out.unmet_comm_deficit_mbps,
                    "service_level_ratio":          out.service_level_ratio,
                    "activation_status":            out.activation_status,
                }
            })
        return json.dumps({"outputs": result}, ensure_ascii=False, indent=2)


# 6. DEMO / TEST

def build_demo_state() -> tuple[GridState, list[Node]]:
    """Test için sabit örnek veri."""
    grid = GridState(
        total_grid_power_kw=10000.0,
        total_microgrid_power_kw=2500.0,
        total_comm_capacity_mbps=1000.0,
    )

    # priority_weight = TOPSIS skoru (Gizem Dinçer, IE)
    # * geçici — Gizem onayı bekleniyor
    raw_nodes = [
        ("NODE_KOU_HASTANE",   "KOU Hastanesi",       "İzmit TM",     "Kritik_Saglik",
         0.91, 5000.0, 2500.0, 6000.0, 1000.0, 0.50, 0.95, 50.0,  10.0,  "düşük", 2.0),
        ("NODE_GEBZE_HASTANE", "Gebze Hastanesi",      "Gebze OSB TM", "Kritik_Saglik",
         0.88, 4000.0, 2000.0, 5000.0, 800.0,  0.50, 0.90, 40.0,  10.0,  "düşük", 2.0),  # * geçici
        ("NODE_112_CAGRI",     "112 Acil",             "Köseköy TM",   "Kritik_Iletisim",
         0.86, 130.0,  100.0,  160.0,  80.0,   1.00, 0.90, 80.0,  40.0,  "yüksek",6.0),  # * geçici
        ("NODE_AFAD_MERKEZ",   "AFAD Kocaeli",         "Köseköy TM",   "Kritik_Koordinasyon",
         0.84, 210.0,  160.0,  260.0,  150.0,  1.00, 0.90, 100.0, 50.0,  "orta",  4.0),
        ("NODE_BAZ_YARIMCA",   "Yarımca Baz İst.",     "Yarımca TM",   "Haberlesme_Omurga",
         0.72, 50.0,   20.0,   70.0,   30.0,   0.80, 0.85, 200.0, 100.0, "yüksek",6.0),
        ("NODE_SU_POMPASI",    "Arslanbey Su Pompası", "Arslanbey TM", "Kritik_Altyapi",
         0.63, 250.0,  150.0,  300.0,  50.0,   0.60, 0.85, 20.0,  5.0,   "orta",  8.0),
    ]

    nodes = []
    for r in raw_nodes:
        nodes.append(Node(
            node_id=r[0], node_name=r[1], location=r[2], node_type=r[3],
            parameters=NodeParameters(
                priority_weight=r[4],            demand_power_kw=r[5],
                min_required_power_kw=r[6],      max_acceptable_power_kw=r[7],
                max_v2g_support_kw=r[8],         min_service_ratio=r[9],
                initial_reliability_score=r[10], demand_comm_mbps=r[11],
                min_required_comm_mbps=r[12],    outage_risk_level=r[13],
                recovery_time_hrs=r[14],
            )
        ))
    return grid, nodes

# 7. INFLUXDB YAZICI

"""
import urllib.request

class InfluxDBWriter:
    def __init__(self):
        self.url    = "http://192.168.1.216:8086"
        self.db     = "afet_db"
        log.info("InfluxDB 3 bağlantısı hazır.")

    def write(self, outputs: list[DecisionOutput]) -> None:
        lines = []
        for out in outputs:
            line = (
                f"karar_motoru,"
                f"node_id={out.node_id} "
                f"activation_status={out.activation_status},"
                f"service_level_ratio={out.service_level_ratio},"
                f"allocated_grid_power_kw={out.allocated_grid_power_kw},"
                f"allocated_mg_power_kw={out.allocated_mg_power_kw},"
                f"unmet_energy_deficit_kw={out.unmet_energy_deficit_kw}"
            )
            lines.append(line)

        body    = "\n".join(lines).encode("utf-8")
        req_url = f"{self.url}/api/v3/write_lp?db={self.db}"
        req     = urllib.request.Request(
            req_url,
            data=body,
            method="POST",
            headers={"Content-Type": "text/plain; charset=utf-8"}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                log.info(f"InfluxDB'ye {len(outputs)} düğüm yazıldı. Status: {resp.status}")
        except Exception as ex:
            log.error(f"InfluxDB yazma hatası: {ex}")

    def close(self):
        log.info("InfluxDB bağlantısı kapatıldı.")"""

def load_scenario_from_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    grid = GridState(
        total_grid_power_kw=data["grid_state"]["total_grid_power_kw"],
        total_microgrid_power_kw=data["grid_state"]["total_microgrid_power_kw"],
        total_comm_capacity_mbps=data["grid_state"]["total_comm_capacity_mbps"]
    )

    nodes = []
    for nd in data["nodes"]:
        p = nd["parameters"]
        # NodeState yerine Node ve NodeParameters sınıflarını kullanıyoruz
        node = Node(
            node_id=nd["node_id"],
            node_name=nd["node_name"],
            location=nd["location"],
            node_type=nd["node_type"],
            parameters=NodeParameters(
                priority_weight=p["priority_weight"],
                demand_power_kw=p["demand_power_kw"],
                min_required_power_kw=p["min_required_power_kw"],
                max_acceptable_power_kw=p["max_acceptable_power_kw"],
                max_v2g_support_kw=p["max_v2g_support_kw"],
                min_service_ratio=p["min_service_ratio"],
                initial_reliability_score=p["initial_reliability_score"],
                demand_comm_mbps=p["demand_comm_mbps"],
                min_required_comm_mbps=p["min_required_comm_mbps"],
                outage_risk_level=p["outage_risk_level"],
                recovery_time_hrs=p["recovery_time_hrs"]
            )
        )
        nodes.append(node)
    
    return grid, nodes
"""
if __name__ == "__main__":
    print("JSON Senaryosu Yükleniyor...")
    grid, nodes = load_scenario_from_json("senaryo1.json")

    print("\n" + "="*60)
    print("SENARYO 1: Büyük Deprem (Kısıtlı Kapasite) — MILPSolver")
    print("="*60)
    
    engine_milp = DecisionEngine(use_milp=True)
    engine_milp.on_islanding_detected(grid, nodes) """
"""
    # --- InfluxDB'ye yaz ---
    print("\n" + "="*60)
    print("INFLUXDB YAZMA TESTİ")
    print("="*60)
    try:
        writer = InfluxDBWriter()

        # Senaryo 1 çıktılarını yaz
        log.info("Senaryo 1 çıktıları yazılıyor...")
        writer.write(engine.last_outputs)

        # Senaryo 2 çıktılarını yaz
        log.info("Senaryo 2 çıktıları yazılıyor...")
        writer.write(engine_milp.last_outputs)

        writer.close()
        print("\n✓ Tüm veriler InfluxDB'ye başarıyla yazıldı!")
        print("  Ege Grafana'da kontrol edebilir.")

    except Exception as ex:
        log.error(f"InfluxDB yazma hatası: {ex}")"""
        
# --- MQTT AYARLARI VE CANLI DİNLEYİCİ ---
MQTT_BROKER = "172.20.10.3"  # Mutlaka bu şekilde güncellenmeli
MQTT_PORT = 1884             # Port 1884 olarak kalmalı
TOPIC_SUB = "kocaeli_grid/sensors/live_state"
TOPIC_PUB = "kocaeli_grid/commands/relays"

engine = DecisionEngine(use_milp=True)

def on_connect(client, userdata, flags, rc):
    print(f"\n[BİLGİ] MQTT Sunucusuna bağlanıldı (Kod: {rc})")
    client.subscribe(TOPIC_SUB)
    print(f"[DİNLENİYOR] '{TOPIC_SUB}' kanalı aktif, Nazenin'den veri bekleniyor...\n")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        print("\n--- CANLI VERİ PAKETİ GELDİ ---")

        # 1. VERİ DOĞRULAMA (Veri eksik gelirse sistemin çökmesini engeller)
        if "grid_state" not in data or "nodes" not in data:
            raise ValueError("Eksik JSON formatı: 'grid_state' veya 'nodes' bulunamadı.")

        grid = GridState(
            total_grid_power_kw=data["grid_state"]["total_grid_power_kw"],
            total_microgrid_power_kw=data["grid_state"]["total_microgrid_power_kw"],
            total_comm_capacity_mbps=data["grid_state"]["total_comm_capacity_mbps"]
        )

        nodes = []
        for nd in data["nodes"]:
            p = nd["parameters"]
            node = Node(
                node_id=nd["node_id"],
                node_name=nd["node_name"],
                location=nd["location"],
                node_type=nd["node_type"],
                parameters=NodeParameters(
                    priority_weight=p["priority_weight"],
                    demand_power_kw=p["demand_power_kw"],
                    min_required_power_kw=p["min_required_power_kw"],
                    max_acceptable_power_kw=p["max_acceptable_power_kw"],
                    max_v2g_support_kw=p["max_v2g_support_kw"],
                    min_service_ratio=p["min_service_ratio"],
                    initial_reliability_score=p["initial_reliability_score"],
                    demand_comm_mbps=p["demand_comm_mbps"],
                    min_required_comm_mbps=p["min_required_comm_mbps"],
                    outage_risk_level=p["outage_risk_level"],
                    recovery_time_hrs=p["recovery_time_hrs"]
                )
            )
            nodes.append(node)

        # 2. ADA MODU KONTROLÜ (Sensör gürültüsü payı bırakılarak 10'dan küçükse tetiklenir)
        if grid.total_grid_power_kw < 10.0:
            print(f"Ada Modu Tespit Edildi! (Şebeke: {grid.total_grid_power_kw} kW) Karar Motoru hesaplıyor...")
            results = engine.on_islanding_detected(grid, nodes)

            commands = {out.node_id: out.activation_status for out in results}
            client.publish(TOPIC_PUB, json.dumps(commands))
            print(f"[İLETİLDİ] Röle Komutları Gönderildi: {commands}")
        else:
            print(f"[NORMAL] Şebeke Stabil (Güç: {grid.total_grid_power_kw} kW). Otonom müdahaleye gerek yok.")

    # 3. SPESİFİK HATA YAKALAYICILAR
    except json.JSONDecodeError:
        print("[HATA] Gelen veri geçerli bir JSON formatında değil! (Bozuk Paket)")
    except KeyError as ke:
        print(f"[HATA] Beklenen veri anahtarı bulunamadı: {ke}")
    except ValueError as ve:
        print(f"[HATA] {ve}")
    except Exception as e:
        print(f"[KRİTİK HATA] Veri işleme sırasında beklenmeyen bir sorun oluştu: {e}")

# --- ANA ÇALIŞTIRMA BLOĞU ---
if __name__ == "__main__":
    # Paho-MQTT v2 sürüm uyarısını çözmek için API versiyonunu belirtiyoruz
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message

    print("Bağlantı kuruluyor...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()