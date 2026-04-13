import os
import sys
import time
import subprocess
import threading
import xmlrpc.client
from datetime import datetime
from xmlrpc.server import SimpleXMLRPCServer
from socketserver import ThreadingMixIn
from config import (
    MASTER_IP, MASTER_PORT, WORKER_TIMEOUT,
    REGISTRY_IP, REGISTRY_PORT,
    AUTO_SCALE, WORKER_PORT_RANGE, SCALE_UP_THRESHOLD,
    SCALE_DOWN_IDLE, MIN_WORKERS, MAX_WORKERS,
)


def ts():
    return datetime.now().strftime("%H:%M:%S")


# Threaded server so multiple clients can connect at the same time
class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass


# Custom transport to enforce per-call timeout on worker connections
class TimeoutTransport(xmlrpc.client.Transport):
    def __init__(self, timeout):
        super().__init__()
        self._timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn


# -- Registry proxy ----------------------------------------------------

def get_registry():
    """Create a fresh proxy to the service discovery registry."""
    return xmlrpc.client.ServerProxy(
        f"http://{REGISTRY_IP}:{REGISTRY_PORT}/",
        allow_none=True,
    )


def fetch_workers():
    """Fetch current live worker list from the registry."""
    try:
        return get_registry().get_workers()
    except Exception as e:
        print(f"[{ts()}] [Master] WARNING: Registry unreachable ({e})", flush=True)
        return []


# -- Shared state (protected by lock where needed) ---------------------

task_table = {}       # task_id -> {status, worker, result}
task_counter = [100]  # auto-increment task ID
rr_index = [0]        # round-robin pointer
lock = threading.Lock()

# Track last task time per worker (for scale-down decisions)
worker_last_task = {}   # worker_id -> timestamp of last task
worker_last_task_lock = threading.Lock()


# -- RPC Methods (called by client / stress_test) ----------------------

def submit_task(task_type, task_data):
    # Assign task ID
    with lock:
        task_counter[0] += 1
        task_id = task_counter[0]

    task_table[task_id] = {"status": "PENDING", "worker": None, "result": None}
    print(f"\n[{ts()}] [Master] Task {task_id} submitted: {task_type}({task_data})", flush=True)

    # Fetch live workers from registry (no hardcoded list!)
    workers = fetch_workers()

    if not workers:
        task_table[task_id]["status"] = "FAILED"
        task_table[task_id]["result"] = "Service Unavailable"
        print(f"[{ts()}] [Master] Task {task_id} FAILED -- Service Unavailable (no workers registered)", flush=True)
        return {
            "taskID": task_id,
            "status": "FAILED",
            "result": "Service Unavailable",
            "workerID": None,
        }

    # Pick starting worker via round-robin
    with lock:
        start_idx = rr_index[0]
        rr_index[0] = (rr_index[0] + 1) % len(workers)

    # Try each worker in round-robin order; fall back on failure
    for i in range(len(workers)):
        worker = workers[(start_idx + i) % len(workers)]
        print(f"[{ts()}] [Master] Assigning task {task_id} to {worker['id']}", flush=True)

        task_table[task_id]["status"] = "RUNNING"
        task_table[task_id]["worker"] = worker["id"]

        try:
            proxy = xmlrpc.client.ServerProxy(
                f"http://{worker['host']}:{worker['port']}/",
                transport=TimeoutTransport(WORKER_TIMEOUT),
                allow_none=True,
            )
            result = proxy.execute_task(task_id, task_type, task_data)
            task_table[task_id]["status"] = result["status"]
            task_table[task_id]["result"] = result["result"]
            print(f"[{ts()}] [Master] Task {task_id} -> {result['status']} | Result: {result['result']}", flush=True)

            # Track last task time for this worker (used by auto-scaler)
            with worker_last_task_lock:
                worker_last_task[worker["id"]] = time.time()

            return result

        except Exception as e:
            print(f"[{ts()}] [Master] {worker['id']} unreachable ({e}). Trying next worker...", flush=True)

    # All workers failed
    task_table[task_id]["status"] = "FAILED"
    task_table[task_id]["result"] = "Service Unavailable"
    print(f"[{ts()}] [Master] Task {task_id} FAILED -- Service Unavailable (all workers unreachable)", flush=True)
    return {
        "taskID": task_id,
        "status": "FAILED",
        "result": "Service Unavailable",
        "workerID": None,
    }


def get_task_status(task_id):
    if task_id not in task_table:
        return {"taskID": task_id, "status": "NOT_FOUND", "worker": None, "result": None}
    t = task_table[task_id]
    return {"taskID": task_id, "status": t["status"], "worker": t["worker"], "result": t["result"]}


def get_all_tasks():
    return [
        {"taskID": k, "status": v["status"], "worker": v["worker"], "result": v["result"]}
        for k, v in task_table.items()
    ]


def get_cluster_status():
    """Return current cluster state for the client to display."""
    workers = fetch_workers()
    pending = sum(1 for t in task_table.values() if t["status"] == "PENDING")
    running = sum(1 for t in task_table.values() if t["status"] == "RUNNING")
    completed = sum(1 for t in task_table.values() if t["status"] == "COMPLETED")
    failed = sum(1 for t in task_table.values() if t["status"] == "FAILED")
    return {
        "worker_count": len(workers),
        "workers": [f"{w['id']}@{w['host']}:{w['port']}" for w in workers],
        "pending_tasks": pending,
        "running_tasks": running,
        "completed_tasks": completed,
        "failed_tasks": failed,
        "auto_scale": AUTO_SCALE,
        "auto_scale_range": f"{MIN_WORKERS}-{MAX_WORKERS}" if AUTO_SCALE else "disabled",
        "spawned_workers": list(spawned_processes.keys()),
    }


# -- Auto-Scaler -------------------------------------------------------

spawned_processes = {}   # worker_id -> subprocess.Popen object
spawned_lock = threading.Lock()


def find_available_port():
    """Find the next available port in WORKER_PORT_RANGE not used by any registered worker."""
    workers = fetch_workers()
    used_ports = {w["port"] for w in workers}
    for port in range(WORKER_PORT_RANGE[0], WORKER_PORT_RANGE[1] + 1):
        if port not in used_ports:
            return port
    return None


def scale_up():
    """Spawn a new worker process."""
    port = find_available_port()
    if port is None:
        print(f"[{ts()}] [AutoScaler] Cannot scale up -- no available ports in range {WORKER_PORT_RANGE}", flush=True)
        return False

    worker_id = f"Worker{port - 8000}"
    print(f"[{ts()}] [AutoScaler] Scaling UP -- spawning {worker_id} on port {port}", flush=True)

    # Spawn worker as a subprocess
    python_exe = sys.executable
    worker_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "worker.py")
    proc = subprocess.Popen(
        [python_exe, worker_script, str(port)],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )

    with spawned_lock:
        spawned_processes[worker_id] = proc

    print(f"[{ts()}] [AutoScaler] {worker_id} spawned (PID: {proc.pid})", flush=True)
    return True


def scale_down(worker_id):
    """Terminate a spawned worker process."""
    with spawned_lock:
        proc = spawned_processes.get(worker_id)
        if proc is None:
            return False

        print(f"[{ts()}] [AutoScaler] Scaling DOWN -- terminating {worker_id} (PID: {proc.pid})", flush=True)
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        del spawned_processes[worker_id]

    print(f"[{ts()}] [AutoScaler] {worker_id} terminated", flush=True)
    return True


def auto_scaler_loop():
    """Background thread that monitors load and scales workers up/down."""
    print(f"[{ts()}] [AutoScaler] Started (min={MIN_WORKERS}, max={MAX_WORKERS}, "
          f"threshold={SCALE_UP_THRESHOLD} tasks/worker, idle={SCALE_DOWN_IDLE}s)", flush=True)

    while True:
        time.sleep(5)  # check every 5 seconds

        try:
            workers = fetch_workers()
            worker_count = len(workers)

            # Count pending/running tasks
            pending = sum(1 for t in task_table.values() if t["status"] in ("PENDING", "RUNNING"))

            # -- Scale UP --
            if worker_count < MAX_WORKERS:
                if worker_count == 0 or (pending / max(worker_count, 1)) > SCALE_UP_THRESHOLD:
                    scale_up()

            # -- Scale DOWN --
            if worker_count > MIN_WORKERS and pending == 0:
                now = time.time()
                with spawned_lock:
                    # Only scale down workers we spawned (not manually started ones)
                    for wid in list(spawned_processes.keys()):
                        with worker_last_task_lock:
                            last = worker_last_task.get(wid, 0)
                        if now - last > SCALE_DOWN_IDLE:
                            scale_down(wid)
                            break  # scale down one at a time

            # -- Ensure minimum workers --
            if worker_count < MIN_WORKERS:
                deficit = MIN_WORKERS - worker_count
                for _ in range(deficit):
                    scale_up()

            # Clean up terminated processes
            with spawned_lock:
                dead = [wid for wid, p in spawned_processes.items() if p.poll() is not None]
                for wid in dead:
                    del spawned_processes[wid]

        except Exception as e:
            print(f"[{ts()}] [AutoScaler] Error: {e}", flush=True)


# -- Main --------------------------------------------------------------

if __name__ == "__main__":
    # Start auto-scaler if enabled
    if AUTO_SCALE:
        scaler_thread = threading.Thread(target=auto_scaler_loop, daemon=True)
        scaler_thread.start()

    server = ThreadedXMLRPCServer(
        ("0.0.0.0", MASTER_PORT), logRequests=False, allow_none=True
    )
    server.register_function(submit_task, "submit_task")
    server.register_function(get_task_status, "get_task_status")
    server.register_function(get_all_tasks, "get_all_tasks")
    server.register_function(get_cluster_status, "get_cluster_status")

    print(f"[{ts()}] [Master] Running on 0.0.0.0:{MASTER_PORT} (clients connect via {MASTER_IP}:{MASTER_PORT})", flush=True)
    print(f"[{ts()}] [Master] Registry: {REGISTRY_IP}:{REGISTRY_PORT}", flush=True)
    print(f"[{ts()}] [Master] Auto-scaling: {'ON' if AUTO_SCALE else 'OFF'}", flush=True)

    # Show currently registered workers
    workers = fetch_workers()
    if workers:
        print(f"[{ts()}] [Master] Workers discovered: {[w['id'] + '@' + w['host'] + ':' + str(w['port']) for w in workers]}", flush=True)
    else:
        print(f"[{ts()}] [Master] No workers registered yet (they will appear as they start)", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{ts()}] [Master] Shutting down...", flush=True)
        # Terminate any auto-scaled workers
        with spawned_lock:
            for wid, proc in spawned_processes.items():
                print(f"[{ts()}] [Master] Terminating auto-scaled {wid} (PID: {proc.pid})", flush=True)
                try:
                    proc.terminate()
                except Exception:
                    pass
        server.server_close()
        print(f"[{ts()}] [Master] Done.", flush=True)
