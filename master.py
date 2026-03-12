import threading
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer
from socketserver import ThreadingMixIn
from config import WORKERS, MASTER_HOST, MASTER_PORT, WORKER_TIMEOUT


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


# Shared state (protected by lock where needed)
task_table = {}       # task_id -> {status, worker, result}
task_counter = [100]  # auto-increment task ID
rr_index = [0]        # round-robin pointer
lock = threading.Lock()


def submit_task(task_type, task_data):
    # Assign task ID and register in table
    with lock:
        task_counter[0] += 1
        task_id = task_counter[0]
        start_idx = rr_index[0]
        rr_index[0] = (rr_index[0] + 1) % len(WORKERS)

    task_table[task_id] = {"status": "PENDING", "worker": None, "result": None}
    print(f"\n[Master] Task {task_id} submitted: {task_type}({task_data})")

    # Try each worker in round-robin order; fall back on failure
    for i in range(len(WORKERS)):
        worker = WORKERS[(start_idx + i) % len(WORKERS)]
        print(f"[Master] Assigning task {task_id} to {worker['id']}")

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
            print(f"[Master] Task {task_id} → {result['status']} | Result: {result['result']}")
            return result

        except Exception as e:
            print(f"[Master] {worker['id']} unreachable ({e}). Trying next worker...")

    # All workers failed
    task_table[task_id]["status"] = "FAILED"
    task_table[task_id]["result"] = "All workers unavailable"
    print(f"[Master] Task {task_id} FAILED — no available workers")
    return {
        "taskID": task_id,
        "status": "FAILED",
        "result": "All workers unavailable",
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


if __name__ == "__main__":
    server = ThreadedXMLRPCServer(
        (MASTER_HOST, MASTER_PORT), logRequests=False, allow_none=True
    )
    server.register_function(submit_task, "submit_task")
    server.register_function(get_task_status, "get_task_status")
    server.register_function(get_all_tasks, "get_all_tasks")
    print(f"[Master] Running on {MASTER_HOST}:{MASTER_PORT}")
    print(f"[Master] Workers registered: {[w['id'] for w in WORKERS]}")
    server.serve_forever()
