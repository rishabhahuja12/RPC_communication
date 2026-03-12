import sys
from datetime import datetime
from xmlrpc.server import SimpleXMLRPCServer
from tasks import TASK_HANDLERS

worker_id = None


def ts():
    return datetime.now().strftime("%H:%M:%S")


def execute_task(task_id, task_type, task_data):
    print(f"[{ts()}] [{worker_id}] Task {task_id} received: {task_type}({task_data})")

    if task_type not in TASK_HANDLERS:
        print(f"[{ts()}] [{worker_id}] Unknown task type: {task_type}")
        return {
            "taskID": task_id,
            "status": "FAILED",
            "result": f"Unknown task type: {task_type}",
            "workerID": worker_id,
        }

    try:
        result = TASK_HANDLERS[task_type](task_data)
        print(f"[{ts()}] [{worker_id}] Task {task_id} completed. Result: {result}")
        return {
            "taskID": task_id,
            "status": "COMPLETED",
            "result": result,
            "workerID": worker_id,
        }
    except Exception as e:
        print(f"[{ts()}] [{worker_id}] Task {task_id} failed: {e}")
        return {
            "taskID": task_id,
            "status": "FAILED",
            "result": str(e),
            "workerID": worker_id,
        }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python worker.py <port>")
        print("Example: python worker.py 8001")
        sys.exit(1)

    port = int(sys.argv[1])
    worker_id = f"Worker{port - 8000}"

    server = SimpleXMLRPCServer(("0.0.0.0", port), logRequests=False, allow_none=True)
    server.register_function(execute_task, "execute_task")
    print(f"[{ts()}] [{worker_id}] Running on 0.0.0.0:{port} (accepting connections from any machine). Waiting for tasks...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{ts()}] [{worker_id}] Shutting down.")
        server.server_close()
