import threading
import uuid
import xmlrpc.client
import time
from config import MASTER_IP, MASTER_PORT

# -- CONFIGURE ---------------------
NUM_TASKS = 20   # total tasks to fire simultaneously
# -----------------------------------

results = {}
lock = threading.Lock()


def submit(task_num, client_id):
    master = xmlrpc.client.ServerProxy(
        f"http://{MASTER_IP}:{MASTER_PORT}/",
        allow_none=True,
    )
    # Cycle through different task types to make it more interesting
    task_type = ["factorial", "add", "reverse"][task_num % 3]

    if task_type == "factorial":
        task_data = [task_num % 10 + 1]          # factorial(1) to factorial(10)
    elif task_type == "add":
        task_data = [task_num * 10, task_num * 5] # add(N*10, N*5)
    else:
        task_data = [f"stress{task_num}"]         # reverse("stressN")

    result = master.submit_task(client_id, task_type, task_data)

    with lock:
        results[task_num] = {**result, "task_type": task_type, "task_data": task_data}
        print(
            f"  #{task_num:>3} | {task_type:<10} | "
            f"{str(result['status']):<10} | Result: {result['result']}"
        )


def main():
    client_id = f"StressTest_{uuid.uuid4().hex[:8]}"

    print("=" * 70)
    print(f"  STRESS TEST -- Firing {NUM_TASKS} tasks simultaneously")
    print(f"  Target master: {MASTER_IP}:{MASTER_PORT}")
    print(f"  Client ID: {client_id}")
    print("=" * 70)

    threads = [threading.Thread(target=submit, args=(i, client_id)) for i in range(NUM_TASKS)]

    start = time.time()

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    elapsed = time.time() - start

    # Summary
    completed = sum(1 for r in results.values() if r["status"] == "COMPLETED")
    failed = sum(1 for r in results.values() if r["status"] == "FAILED")

    print("\n" + "=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Total tasks    : {NUM_TASKS}")
    print(f"  Completed      : {completed}")
    print(f"  Failed         : {failed}")
    print(f"  Time taken     : {elapsed:.2f} seconds")
    print("=" * 70)


if __name__ == "__main__":
    main()
