import sys
from xmlrpc.server import SimpleXMLRPCServer
from tasks import TASK_HANDLERS

worker_id = None


def execute_task(task_id, task_type, task_data):
    print(f"[{worker_id}] Task {task_id} received: {task_type}({task_data})")

    if task_type not in TASK_HANDLERS:
        print(f"[{worker_id}] Unknown task type: {task_type}")
        return {
            "taskID": task_id,
            "status": "FAILED",
            "result": f"Unknown task type: {task_type}",
            "workerID": worker_id,
        }

    try:
        result = TASK_HANDLERS[task_type](task_data)
        print(f"[{worker_id}] Task {task_id} completed. Result: {result}")
        return {
            "taskID": task_id,
            "status": "COMPLETED",
            "result": result,
            "workerID": worker_id,
        }
    except Exception as e:
        print(f"[{worker_id}] Task {task_id} failed: {e}")
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

    server = SimpleXMLRPCServer(("localhost", port), logRequests=False, allow_none=True)
    server.register_function(execute_task, "execute_task")
    print(f"[{worker_id}] Running on localhost:{port}. Waiting for tasks...")
    server.serve_forever()
