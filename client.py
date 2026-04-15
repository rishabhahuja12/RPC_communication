import uuid
import xmlrpc.client
from config import MASTER_IP, MASTER_PORT


def main():
    # Generate a unique client identity (client never sees internal details)
    client_id = f"Client_{uuid.uuid4().hex[:8]}"

    master = xmlrpc.client.ServerProxy(
        f"http://{MASTER_IP}:{MASTER_PORT}/",
        allow_none=True,
    )

    print("=" * 45)
    print("       Distributed Computation Client")
    print("=" * 45)

    while True:
        print("\nOptions:")
        print("  1. Compute")
        print("  2. View past results")
        print("  3. Exit")

        choice = input("\nChoice: ").strip()

        if choice == "1":
            print("\nAvailable operations: add | factorial | reverse")
            task_type = input("Operation: ").strip().lower()

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
                print("Unknown operation. Choose: add | factorial | reverse")
                continue

            print(f"\nProcessing {task_type}({task_data}) ...")
            result = master.submit_task(client_id, task_type, task_data)

            if result["status"] == "COMPLETED":
                # Display result based on task type
                if task_type == "add":
                    print(f"\n  {task_data[0]} + {task_data[1]} = {result['result']}")
                elif task_type == "factorial":
                    print(f"\n  factorial({task_data[0]}) = {result['result']}")
                elif task_type == "reverse":
                    print(f"\n  reverse(\"{task_data[0]}\") = \"{result['result']}\"")
            else:
                print(f"\n  Computation failed. Please try again later.")

        elif choice == "2":
            results = master.get_my_results(client_id)
            if not results:
                print("\nNo past results found.")
            else:
                print(f"\n  Your Past Results:")
                print(f"  {'-' * 55}")
                for i, r in enumerate(results, 1):
                    task = r["task"]
                    inp = r["input"]
                    res = r["result"]
                    status = r["status"]

                    if task == "add":
                        desc = f"{inp[0]} + {inp[1]}"
                    elif task == "factorial":
                        desc = f"factorial({inp[0]})"
                    elif task == "reverse":
                        desc = f"reverse(\"{inp[0]}\")"
                    else:
                        desc = f"{task}({inp})"

                    if status == "COMPLETED":
                        print(f"  {i:>3}. {desc} = {res}")
                    else:
                        print(f"  {i:>3}. {desc} -> FAILED")
                print(f"  {'-' * 55}")

        elif choice == "3":
            print("Goodbye.")
            break

        else:
            print("Invalid choice. Enter 1-3.")


if __name__ == "__main__":
    main()
