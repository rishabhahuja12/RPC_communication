import xmlrpc.client
from config import MASTER_IP, MASTER_PORT


def main():
    master = xmlrpc.client.ServerProxy(
        f"http://{MASTER_IP}:{MASTER_PORT}/",
        allow_none=True,
    )

    print("=" * 60)
    print("         RPC Distributed System — Admin Dashboard")
    print("=" * 60)

    while True:
        print("\nAdmin Options:")
        print("  1. View all tasks")
        print("  2. Check task status (by ID)")
        print("  3. View cluster status")
        print("  4. View client summary")
        print("  5. Exit")

        choice = input("\nChoice: ").strip()

        if choice == "1":
            tasks = master.get_all_tasks()
            if not tasks:
                print("\nNo tasks submitted yet.")
            else:
                print(f"\n  {'ID':<8} {'Type':<12} {'Status':<12} {'Worker':<12} {'Client':<18} Result")
                print(f"  {'-' * 80}")
                for t in tasks:
                    tid = t["taskID"]
                    ttype = str(t.get("task_type", "?"))
                    status = str(t["status"])
                    worker = str(t["worker"]) if t["worker"] else "-"
                    client = str(t.get("client_id", "?"))
                    result = t["result"]
                    print(f"  {tid:<8} {ttype:<12} {status:<12} {worker:<12} {client:<18} {result}")
                print(f"\n  Total tasks: {len(tasks)}")

        elif choice == "2":
            try:
                task_id = int(input("Task ID: "))
            except ValueError:
                print("Invalid ID.")
                continue
            status = master.get_task_status(task_id)
            if status["status"] == "NOT_FOUND":
                print(f"\n  Task {task_id} not found.")
            else:
                print(f"\n  Task {status['taskID']}:")
                print(f"    Type      : {status.get('task_type', '?')}")
                print(f"    Input     : {status.get('task_data', '?')}")
                print(f"    Status    : {status['status']}")
                print(f"    Worker    : {status['worker']}")
                print(f"    Client    : {status.get('client_id', '?')}")
                print(f"    Result    : {status['result']}")

        elif choice == "3":
            cluster = master.get_cluster_status()
            print(f"\n  {'=' * 40}")
            print(f"         Cluster Status")
            print(f"  {'=' * 40}")
            print(f"  Active workers : {cluster['worker_count']}")
            if cluster['workers']:
                for w in cluster['workers']:
                    print(f"    • {w}")
            else:
                print(f"    (none)")
            print(f"  Pending tasks  : {cluster['pending_tasks']}")
            print(f"  Running tasks  : {cluster['running_tasks']}")
            print(f"  Completed      : {cluster['completed_tasks']}")
            print(f"  Failed         : {cluster['failed_tasks']}")
            print(f"  Auto-scaling   : {'ON' if cluster['auto_scale'] else 'OFF'} ({cluster['auto_scale_range']})")
            if cluster['spawned_workers']:
                print(f"  Auto-spawned   : {', '.join(cluster['spawned_workers'])}")
            print(f"  {'=' * 40}")

        elif choice == "4":
            clients = master.get_all_clients()
            if not clients:
                print("\nNo clients have submitted tasks yet.")
            else:
                print(f"\n  {'Client ID':<22} {'Total':<8} {'Done':<8} {'Failed':<8} {'Pending':<8} {'Running':<8}")
                print(f"  {'-' * 62}")
                for c in clients:
                    cid = c["client_id"]
                    total = c["total"]
                    done = c["completed"]
                    fail = c["failed"]
                    pend = c["pending"]
                    run = c["running"]
                    print(f"  {cid:<22} {total:<8} {done:<8} {fail:<8} {pend:<8} {run:<8}")
                print(f"\n  Total clients: {len(clients)}")

        elif choice == "5":
            print("Exiting admin dashboard.")
            break

        else:
            print("Invalid choice. Enter 1-5.")


if __name__ == "__main__":
    main()
