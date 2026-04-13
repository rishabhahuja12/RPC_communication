import sys
import threading
import time
import xmlrpc.client
from datetime import datetime
from xmlrpc.server import SimpleXMLRPCServer
from tasks import TASK_HANDLERS
from config import REGISTRY_IP, REGISTRY_PORT, HEARTBEAT_INTERVAL

worker_id = None
worker_host = None
worker_port = None


def ts():
    return datetime.now().strftime("%H:%M:%S")


# -- Registry communication -------------------------------------------

def get_registry():
    """Create a fresh proxy to the registry server."""
    return xmlrpc.client.ServerProxy(
        f"http://{REGISTRY_IP}:{REGISTRY_PORT}/",
        allow_none=True,
    )


def register_with_registry():
    """Register this worker with the service discovery registry."""
    try:
        registry = get_registry()
        registry.register_worker(worker_id, worker_host, worker_port)
        print(f"[{ts()}] [{worker_id}] Registered with registry at {REGISTRY_IP}:{REGISTRY_PORT}", flush=True)
        return True
    except Exception as e:
        print(f"[{ts()}] [{worker_id}] WARNING: Could not register with registry ({e})", flush=True)
        return False


def deregister_from_registry():
    """Deregister this worker from the registry on shutdown."""
    try:
        registry = get_registry()
        registry.deregister_worker(worker_id)
        print(f"[{ts()}] [{worker_id}] Deregistered from registry", flush=True)
    except Exception:
        pass  # best-effort on shutdown


def heartbeat_loop():
    """Send heartbeat to registry every HEARTBEAT_INTERVAL seconds."""
    while True:
        try:
            registry = get_registry()
            alive = registry.heartbeat(worker_id)
            if not alive:
                # Registry doesn't know us -- re-register
                print(f"[{ts()}] [{worker_id}] Re-registering with registry (heartbeat returned False)", flush=True)
                registry.register_worker(worker_id, worker_host, worker_port)
        except Exception:
            pass  # registry might be temporarily down, keep trying
        time.sleep(HEARTBEAT_INTERVAL)


# -- Task execution (unchanged) ----------------------------------------

def execute_task(task_id, task_type, task_data):
    print(f"[{ts()}] [{worker_id}] Task {task_id} received: {task_type}({task_data})", flush=True)

    if task_type not in TASK_HANDLERS:
        print(f"[{ts()}] [{worker_id}] Unknown task type: {task_type}", flush=True)
        return {
            "taskID": task_id,
            "status": "FAILED",
            "result": f"Unknown task type: {task_type}",
            "workerID": worker_id,
        }

    try:
        result = TASK_HANDLERS[task_type](task_data)
        print(f"[{ts()}] [{worker_id}] Task {task_id} completed. Result: {result}", flush=True)
        return {
            "taskID": task_id,
            "status": "COMPLETED",
            "result": result,
            "workerID": worker_id,
        }
    except Exception as e:
        print(f"[{ts()}] [{worker_id}] Task {task_id} failed: {e}", flush=True)
        return {
            "taskID": task_id,
            "status": "FAILED",
            "result": str(e),
            "workerID": worker_id,
        }


# -- Main --------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python worker.py <port> [--host <ip>]")
        print("Example: python worker.py 8001")
        print("Example: python worker.py 8001 --host 192.168.1.50")
        sys.exit(1)

    worker_port = int(sys.argv[1])
    worker_id = f"Worker{worker_port - 8000}"

    # Optional --host flag for LAN deployments (default: localhost)
    worker_host = "localhost"
    if "--host" in sys.argv:
        host_idx = sys.argv.index("--host")
        if host_idx + 1 < len(sys.argv):
            worker_host = sys.argv[host_idx + 1]

    # Register with the service discovery registry
    register_with_registry()

    # Start heartbeat thread (daemon -- dies with main thread)
    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()
    print(f"[{ts()}] [{worker_id}] Heartbeat thread started (interval: {HEARTBEAT_INTERVAL}s)", flush=True)

    # Start XML-RPC server
    server = SimpleXMLRPCServer(("0.0.0.0", worker_port), logRequests=False, allow_none=True)
    server.register_function(execute_task, "execute_task")
    print(f"[{ts()}] [{worker_id}] Running on 0.0.0.0:{worker_port} (accepting connections from any machine). Waiting for tasks...", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{ts()}] [{worker_id}] Shutting down...", flush=True)
        deregister_from_registry()
        server.server_close()
        print(f"[{ts()}] [{worker_id}] Done.", flush=True)
