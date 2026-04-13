# -------------------------------------------------------------
#  HOW TO FIND YOUR LAN IP:
#    Windows  ->  run  ipconfig        look for "IPv4 Address"
#    Mac/Linux -> run  ifconfig        look for "inet" under en0/eth0
#
#  All machines must be connected to the SAME WiFi or LAN.
#  For local single-machine testing, keep everything as "localhost".
# -------------------------------------------------------------

# IP of the machine running master.py
# -> Used by client.py and stress_test.py to connect to the master
MASTER_IP   = "localhost"       # <- replace with master machine's LAN IP
MASTER_PORT = 9000

# -------------------------------------------------------------
#  SERVICE DISCOVERY -- Registry Server
#  Workers register here on startup. Master queries here for
#  the live worker list. No more hardcoded worker IPs!
# -------------------------------------------------------------
REGISTRY_IP   = "localhost"     # <- replace with registry machine's LAN IP
REGISTRY_PORT = 7000

HEARTBEAT_INTERVAL = 3          # seconds -- workers send heartbeat this often
HEARTBEAT_TIMEOUT  = 10         # seconds -- registry removes worker if no heartbeat

WORKER_TIMEOUT = 5              # seconds -- if worker doesn't respond in 5s, reassign

# -------------------------------------------------------------
#  AUTO-SCALING (master spawns/kills worker processes on demand)
#  Only works for workers on the same machine as the master.
#  Remote workers must be started manually (they self-register).
# -------------------------------------------------------------
AUTO_SCALE         = True
WORKER_PORT_RANGE  = (8001, 8020)   # ports auto-scaler can use for new workers
SCALE_UP_THRESHOLD = 2              # pending tasks per worker before scaling up
SCALE_DOWN_IDLE    = 30             # seconds a worker must be idle before scaling down
MIN_WORKERS        = 2              # never scale below this
MAX_WORKERS        = 6              # never scale above this
