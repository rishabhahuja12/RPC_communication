WORKERS = [
    {"id": "Worker1", "host": "localhost", "port": 8001},
    {"id": "Worker2", "host": "localhost", "port": 8002},
]

MASTER_HOST = "localhost"
MASTER_PORT = 9000

WORKER_TIMEOUT = 5  # seconds — if worker doesn't respond in 5s, reassign
