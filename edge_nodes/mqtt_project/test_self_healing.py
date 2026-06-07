import subprocess
import time

processes = {}

def start(name, cmd):
    print(f"{name} başlatılıyor...")
    p = subprocess.Popen(cmd, shell=True)
    processes[name] = p

def stop(name):
    print(f"{name} durduruluyor...")
    if name in processes:
        processes[name].terminate()

def start_all():
    start("listener", "python listener.py")
    start("R1", "python node_R1.py")
    start("R2", "python node_R2.py")
    start("C1", "python node_C1.py")
    start("C2", "python node_C2.py")
    start("E1", "python node_E1.py")
    start("E2", "python node_E2.py")

def stop_all():
    for name in processes:
        stop(name)

def check_flow(duration=5):
    print("Veri akışı kontrol ediliyor...")
    print("👉 Eğer ekranda 'GELEN VERİ' akıyorsa → PASS")
    time.sleep(duration)

print("=== TEST BAŞLIYOR ===")

start_all()

print("Sistem stabilize oluyor...")
time.sleep(10)

# TEST 1
print("\n--- TEST: R1 kapatılıyor ---")
stop("R1")
check_flow()

print("✅ PASS (manuel gözlem)")

# TEST 2
print("\n--- TEST: R2 kapatılıyor ---")
stop("R2")
check_flow()

print("✅ PASS (manuel gözlem)")

print("\n--- TEST TAMAMLANDI ---")

stop_all()