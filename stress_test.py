import threading
import xmlrpc.client
import time
from config import MASTER_IP, MASTER_PORT

# -- CONFIGURE ---------------------
NUM_TASKS = 20   # total tasks to fire simultaneously
# -----------------------------------

results = {}
lock = threading.Lock()


def submit(task_num):
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

    result = master.submit_task(task_type, task_data)

    with lock:
        results[task_num] = result
        worker_name = str(result['workerID']) if result['workerID'] else "None"
        print(
            f"  Task {result['taskID']:>4} | {task_type:<10} | "
            f"{str(result['status']):<10} | Worker: {worker_name:<10} | Result: {result['result']}"
        )


def main():
    print("=" * 70)
    print(f"  STRESS TEST -- Firing {NUM_TASKS} tasks simultaneously")
    print(f"  Target master: {MASTER_IP}:{MASTER_PORT}")
    print("=" * 70)

    threads = [threading.Thread(target=submit, args=(i,)) for i in range(NUM_TASKS)]

    start = time.time()

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    elapsed = time.time() - start

    # Summary
    worker_counts = {}
    completed = sum(1 for r in results.values() if r["status"] == "COMPLETED")
    failed = sum(1 for r in results.values() if r["status"] == "FAILED")

    for r in results.values():
        w = str(r["workerID"]) if r["workerID"] else "None"
        worker_counts[w] = worker_counts.get(w, 0) + 1

    print("\n" + "=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Total tasks    : {NUM_TASKS}")
    print(f"  Completed      : {completed}")
    print(f"  Failed         : {failed}")
    print(f"  Time taken     : {elapsed:.2f} seconds")
    print(f"  Unique workers : {len([w for w in worker_counts if w != 'None'])}")
    print(f"\n  Tasks per worker:")
    for worker, count in sorted(worker_counts.items()):
        bar = "#" * count
        print(f"    {worker:<12} {bar}  ({count} tasks)")
    print("=" * 70)


if __name__ == "__main__":
    main()
