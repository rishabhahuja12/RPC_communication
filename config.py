# ─────────────────────────────────────────────────────────────
#  HOW TO FIND YOUR LAN IP:
#    Windows  →  run  ipconfig        look for "IPv4 Address"
#    Mac/Linux → run  ifconfig        look for "inet" under en0/eth0
#
#  All machines must be connected to the SAME WiFi or LAN.
#  For local single-machine testing, keep everything as "localhost".
# ─────────────────────────────────────────────────────────────

# IP of the machine running master.py
# → Used by client.py and stress_test.py to connect to the master
MASTER_IP   = "localhost"       # ← replace with master machine's LAN IP
MASTER_PORT = 9000

# IP of each machine running worker.py
# → Used by master.py to send tasks to workers
WORKERS = [
    {"id": "Worker1", "host": "localhost", "port": 8001},  # ← replace with Worker1 machine's LAN IP
    {"id": "Worker2", "host": "localhost", "port": 8002},  # ← replace with Worker2 machine's LAN IP
]

WORKER_TIMEOUT = 5  # seconds — if worker doesn't respond in 5s, reassign
