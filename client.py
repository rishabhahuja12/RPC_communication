import xmlrpc.client
from config import MASTER_HOST, MASTER_PORT


def main():
    master = xmlrpc.client.ServerProxy(
        f"http://{MASTER_HOST}:{MASTER_PORT}/",
        allow_none=True,
    )

    print("=" * 45)
    print("   RPC Distributed Task Execution Client")
    print("=" * 45)

    while True:
        print("\nOptions:")
        print("  1. Submit task")
        print("  2. Check task status")
        print("  3. View all tasks")
        print("  4. Exit")

        choice = input("\nChoice: ").strip()

        if choice == "1":
            print("\nTask types: add | factorial | reverse")
            task_type = input("Task type: ").strip().lower()

            if task_type == "add":
                a = int(input("First number : "))
                b = int(input("Second number: "))
                task_data = [a, b]
            elif task_type == "factorial":
                n = int(input("Number: "))
                task_data = [n]
            elif task_type == "reverse":
                s = input("String: ")
                task_data = [s]
            else:
                print("Unknown task type. Choose: add | factorial | reverse")
                continue

            print(f"\nSubmitting: {task_type}({task_data}) ...")
            result = master.submit_task(task_type, task_data)
            print(f"\n  Task ID : {result['taskID']}")
            print(f"  Status  : {result['status']}")
            print(f"  Result  : {result['result']}")
            print(f"  Worker  : {result['workerID']}")

        elif choice == "2":
            task_id = int(input("Task ID: "))
            status = master.get_task_status(task_id)
            print(f"\n  Task {task_id}:")
            print(f"    Status : {status['status']}")
            print(f"    Worker : {status['worker']}")
            print(f"    Result : {status['result']}")

        elif choice == "3":
            tasks = master.get_all_tasks()
            if not tasks:
                print("\nNo tasks submitted yet.")
            else:
                print(f"\n{'ID':<8} {'Status':<12} {'Worker':<12} Result")
                print("-" * 50)
                for t in tasks:
                    print(f"{t['taskID']:<8} {str(t['status']):<12} {str(t['worker']):<12} {t['result']}")

        elif choice == "4":
            print("Goodbye.")
            break

        else:
            print("Invalid choice. Enter 1–4.")


if __name__ == "__main__":
    main()
