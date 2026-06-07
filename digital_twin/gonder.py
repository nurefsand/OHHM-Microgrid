import paho.mqtt.publish as publish
import json

payload = {
    "grid_state": {
        "total_grid_power_kw": 0.0,
        "total_microgrid_power_kw": 5300.0,
        "total_comm_capacity_mbps": 100.0
    },
    "nodes": [
        {
            "node_id": "NODE_KOU_HASTANE",
            "node_name": "KOU Hastanesi",
            "location": "İzmit TM",
            "node_type": "Kritik_Saglik",
            "parameters": {
                "priority_weight": 0.93,
                "demand_power_kw": 5000.0,
                "min_required_power_kw": 2500.0,
                "max_acceptable_power_kw": 6000.0,
                "max_v2g_support_kw": 1000.0,
                "min_service_ratio": 0.50,
                "initial_reliability_score": 0.95,
                "demand_comm_mbps": 50.0,
                "min_required_comm_mbps": 10.0,
                "outage_risk_level": "düşük",
                "recovery_time_hrs": 2.0
            }
        },
        {
            "node_id": "NODE_AFAD_MERKEZ",
            "node_name": "AFAD Kocaeli",
            "location": "Köseköy TM",
            "node_type": "Kritik_Koordinasyon",
            "parameters": {
                "priority_weight": 0.87,
                "demand_power_kw": 210.0,
                "min_required_power_kw": 160.0,
                "max_acceptable_power_kw": 260.0,
                "max_v2g_support_kw": 5000.0,
                "min_service_ratio": 1.00,
                "initial_reliability_score": 0.90,
                "demand_comm_mbps": 100.0,
                "min_required_comm_mbps": 50.0,
                "outage_risk_level": "orta",
                "recovery_time_hrs": 4.0
            }
        },
        {
            "node_id": "NODE_BAZ_ISTASYONU",
            "node_name": "Yarımca Baz İstasyonu",
            "location": "Yarımca TM",
            "node_type": "Kritik_Haberlesme",
            "parameters": {
                "priority_weight": 0.74,
                "demand_power_kw": 120.0,
                "min_required_power_kw": 60.0,
                "max_acceptable_power_kw": 150.0,
                "max_v2g_support_kw": 50.0,
                "min_service_ratio": 0.50,
                "initial_reliability_score": 0.85,
                "demand_comm_mbps": 200.0,
                "min_required_comm_mbps": 100.0,
                "outage_risk_level": "yüksek",
                "recovery_time_hrs": 6.0
            }
        },
        {
            "node_id": "NODE_SU_POMPASI",
            "node_name": "Arslanbey Su Pompası",
            "location": "Arslanbey TM",
            "node_type": "Kritik_Altyapi",
            "parameters": {
                "priority_weight": 0.66,
                "demand_power_kw": 300.0,
                "min_required_power_kw": 150.0,
                "max_acceptable_power_kw": 400.0,
                "max_v2g_support_kw": 100.0,
                "min_service_ratio": 0.50,
                "initial_reliability_score": 0.80,
                "demand_comm_mbps": 20.0,
                "min_required_comm_mbps": 5.0,
                "outage_risk_level": "orta",
                "recovery_time_hrs": 8.0
            }
        },
        {
            "node_id": "NODE_OSB_SANAYI",
            "node_name": "Gebze OSB",
            "location": "Gebze OSB TM",
            "node_type": "Ertelenebilir_Yuk",
            "parameters": {
                "priority_weight": 0.52,
                "demand_power_kw": 4000.0,
                "min_required_power_kw": 1000.0,
                "max_acceptable_power_kw": 5000.0,
                "max_v2g_support_kw": 0.0,
                "min_service_ratio": 0.25,
                "initial_reliability_score": 0.99,
                "demand_comm_mbps": 10.0,
                "min_required_comm_mbps": 2.0,
                "outage_risk_level": "düşük",
                "recovery_time_hrs": 12.0
            }
        },
        {
            "node_id": "NODE_TRAFO_MERKEZI",
            "node_name": "İzmit 380kV TM İç İhtiyaç",
            "location": "İzmit TM",
            "node_type": "Ertelenebilir_Yuk",
            "parameters": {
                "priority_weight": 0.46,
                "demand_power_kw": 100.0,
                "min_required_power_kw": 50.0,
                "max_acceptable_power_kw": 150.0,
                "max_v2g_support_kw": 0.0,
                "min_service_ratio": 0.50,
                "initial_reliability_score": 0.99,
                "demand_comm_mbps": 5.0,
                "min_required_comm_mbps": 1.0,
                "outage_risk_level": "düşük",
                "recovery_time_hrs": 2.0
            }
        }
    ]
}

publish.single(
    "kocaeli_grid/sensors/live_state",
    json.dumps(payload),
    hostname="172.20.10.2",
    port=1884
)

print("Gönderildi ✅")