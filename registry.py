import threading
import time
from datetime import datetime
from xmlrpc.server import SimpleXMLRPCServer
from socketserver import ThreadingMixIn
from config import REGISTRY_PORT, HEARTBEAT_TIMEOUT


def ts():
    return datetime.now().strftime("%H:%M:%S")


# Threaded server so multiple workers can register/heartbeat concurrently
class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass


# -- Shared state -----------------------------------------------------
# worker_id -> {"host": str, "port": int, "last_heartbeat": float}
worker_pool = {}
pool_lock = threading.Lock()


# -- RPC Methods (called by workers and master) ------------------------

def register_worker(worker_id, host, port):
    """Called by a worker on startup to announce itself."""
    with pool_lock:
        worker_pool[worker_id] = {
            "host": host,
            "port": port,
            "last_heartbeat": time.time(),
        }
    print(f"[{ts()}] [Registry] + Registered {worker_id} at {host}:{port}", flush=True)
    return True


def deregister_worker(worker_id):
    """Called by a worker on graceful shutdown (Ctrl+C)."""
    with pool_lock:
        if worker_id in worker_pool:
            del worker_pool[worker_id]
            print(f"[{ts()}] [Registry] - Deregistered {worker_id} (graceful shutdown)", flush=True)
            return True
    print(f"[{ts()}] [Registry] - Deregister ignored -- {worker_id} not found", flush=True)
    return False


def heartbeat(worker_id):
    """Called by a worker every HEARTBEAT_INTERVAL seconds."""
    with pool_lock:
        if worker_id in worker_pool:
            worker_pool[worker_id]["last_heartbeat"] = time.time()
            return True
    # Worker not registered -- ask it to re-register
    return False


def get_workers():
    """Called by the master to fetch the list of currently healthy workers."""
    with pool_lock:
        return [
            {"id": wid, "host": w["host"], "port": w["port"]}
            for wid, w in worker_pool.items()
        ]


def get_worker_count():
    """Called by the master for quick count (used by auto-scaler)."""
    with pool_lock:
        return len(worker_pool)


# -- Background Reaper Thread -----------------------------------------

def reaper_loop():
    """Remove workers that haven't sent a heartbeat within HEARTBEAT_TIMEOUT."""
    while True:
        time.sleep(5)  # check every 5 seconds
        now = time.time()
        stale = []
        with pool_lock:
            for wid, w in worker_pool.items():
                if now - w["last_heartbeat"] > HEARTBEAT_TIMEOUT:
                    stale.append(wid)
            for wid in stale:
                info = worker_pool.pop(wid)
                print(
                    f"[{ts()}] [Registry] ! Reaped {wid} at {info['host']}:{info['port']} "
                    f"(no heartbeat for {HEARTBEAT_TIMEOUT}s)",
                    flush=True,
                )


# -- Main --------------------------------------------------------------

if __name__ == "__main__":
    # Start the reaper in the background
    reaper_thread = threading.Thread(target=reaper_loop, daemon=True)
    reaper_thread.start()
    print(f"[{ts()}] [Registry] Heartbeat reaper started (timeout: {HEARTBEAT_TIMEOUT}s)", flush=True)

    server = ThreadedXMLRPCServer(
        ("0.0.0.0", REGISTRY_PORT), logRequests=False, allow_none=True
    )
    server.register_function(register_worker, "register_worker")
    server.register_function(deregister_worker, "deregister_worker")
    server.register_function(heartbeat, "heartbeat")
    server.register_function(get_workers, "get_workers")
    server.register_function(get_worker_count, "get_worker_count")

    print(f"[{ts()}] [Registry] Service Discovery running on 0.0.0.0:{REGISTRY_PORT}", flush=True)
    print(f"[{ts()}] [Registry] Waiting for workers to register...", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{ts()}] [Registry] Shutting down.", flush=True)
        server.server_close()
