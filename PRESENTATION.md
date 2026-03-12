# College Project Presentation — RPC Distributed Task Execution System

---

## 1. Final Academic Project Title

**"Design and Implementation of an Enhanced RPC-Based Distributed Task Execution System with Round-Robin Load Balancing, Fault Tolerance, and Real-Time Task Monitoring"**

**Short Title (for slides/report cover):**
*Enhanced RPC-Based Distributed Task Execution System*

---

## 2. Problem Statement

In conventional centralized computing systems, all computational tasks are processed by a single machine, which creates critical limitations in performance, reliability, and scalability. As the volume and complexity of tasks increase, a single machine becomes a bottleneck — slowing execution, exhausting resources, and forming a single point of failure where one crash brings down the entire system. Existing distributed frameworks like Apache Hadoop or Google's gRPC ecosystem, while powerful, introduce significant complexity and dependency overhead that is impractical for lightweight deployments or educational demonstrations. This project addresses these limitations by designing a simplified yet realistic distributed task execution system using XML-RPC, where a central master node distributes computational tasks across multiple worker nodes using round-robin load balancing, automatically detects and recovers from worker failures, and maintains a real-time task status tracking table — demonstrating core distributed computing principles within a minimal, dependency-free Python environment.

---

## 3. Proposed System Explanation

### Overview

The proposed system follows a **Master–Worker architecture** over XML-RPC (Remote Procedure Call), implemented entirely in Python using its standard library. The system consists of three logical layers:

1. **Client Layer** — The user submits tasks through an interactive command-line interface.
2. **Master Layer** — A central coordinator that receives tasks, distributes them using round-robin scheduling, tracks their status, and handles failures.
3. **Worker Layer** — Multiple independent worker processes that listen for RPC calls, execute assigned tasks, and return results.

### Components

| Component | File | Role |
|-----------|------|------|
| Master Node | `master.py` | Task scheduler, load balancer, fault detector |
| Worker Node | `worker.py` | Remote task executor (runs on ports 8001, 8002) |
| Client | `client.py` | User interface for task submission and monitoring |
| Task Definitions | `tasks.py` | Implementations of add, factorial, reverse |
| Configuration | `config.py` | Centralized port/host/timeout settings |

### How It Works

1. The user submits a task (e.g., `factorial(5)`) through `client.py`.
2. The client sends an RPC call to the master at port 9000.
3. The master assigns a unique task ID, records the task as `PENDING`, and selects a worker using round-robin.
4. The master sends an RPC call (`execute_task(task_id, task_type, task_data)`) to the selected worker.
5. The worker executes the function, returns a result dict with `status: COMPLETED`.
6. The master updates the task table to `COMPLETED` and forwards the result to the client.
7. If the worker is unreachable (timeout after 5 seconds), the master catches the exception and reassigns the task to the next available worker.

### Key Features Implemented

- **Round-Robin Load Balancing:** A shared `rr_index` pointer cycles through workers (0 → 1 → 0 → 1...) ensuring equal task distribution.
- **Fault Tolerance:** A `TimeoutTransport` class enforces a 5-second TCP deadline on each worker call. On failure, a retry loop tries the next worker automatically.
- **Real-Time Task Monitoring:** `task_table` dictionary tracks every task through states: `PENDING → RUNNING → COMPLETED / FAILED`.
- **Concurrent Client Handling:** `ThreadingMixIn` enables the master to serve multiple client connections simultaneously.
- **Graceful Degradation:** If all workers fail, the system returns a `FAILED` status without crashing.

---

## 4. Related Work Examples

| System | Similarity to This Project |
|--------|---------------------------|
| **Apache Hadoop MapReduce** | Master–worker architecture; a JobTracker distributes map/reduce tasks to worker TaskTrackers, same as our master distributing tasks to workers |
| **Celery (Python Task Queue)** | Distributed task execution with workers; uses a broker (like RabbitMQ) instead of direct RPC, but the concept of async task assignment and status tracking is identical |
| **Sun RPC / ONC RPC** | The original RPC standard that inspired XML-RPC; used in NFS (Network File System) for remote file operations across networked machines |
| **gRPC (Google)** | Modern, high-performance RPC framework using Protocol Buffers; this project uses XML-RPC as a simpler alternative achieving the same fundamental communication model |
| **Kubernetes (Pod Scheduling)** | The Kubernetes scheduler assigns workloads (pods) to available nodes using resource-aware strategies — analogous to the master assigning tasks to workers |
| **BOINC (Volunteer Computing)** | Distributes scientific computation tasks (e.g., SETI@home) to volunteer machines — conceptually identical to our worker nodes receiving and executing tasks |

---

## 5. 10-Minute PPT Slide Structure

---

### Slide 1 — Title Slide (30 seconds)

- **Title:** Enhanced RPC-Based Distributed Task Execution System
- **Subtitle:** With Load Balancing, Fault Tolerance, and Task Monitoring
- Course name, institute name, team member names, date

---

### Slide 2 — Problem Statement (60 seconds)

- Centralized systems: single machine handles all work
- **3 core problems:**
  - High processing load → slow performance
  - Single point of failure → entire system crashes if one machine fails
  - Poor scalability → adding more tasks makes it worse
- **Solution needed:** Distribute work across multiple machines
- Visual: Single server vs. cluster of servers

---

### Slide 3 — Objective (30 seconds)

- Design a distributed task execution system using RPC
- Implement load balancing across multiple workers
- Handle worker failures automatically (fault tolerance)
- Track task status in real time
- Keep it lightweight — no external dependencies (pure Python)

---

### Slide 4 — System Architecture (90 seconds)

- Show the architecture diagram:
  ```
  CLIENT → MASTER → WORKER 1
                 → WORKER 2
  ```
- Explain each component's role in one line:
  - **Client:** Submits tasks, views results
  - **Master:** Schedules tasks, balances load, detects failures
  - **Workers:** Execute tasks, return results
- Mention: all communication via XML-RPC (Remote Procedure Call)

---

### Slide 5 — What is RPC? (60 seconds)

- RPC = Remote Procedure Call
- Lets a program call a function on **another machine** as if it were local
- Example:
  ```
  # Looks like a local call:
  result = worker.execute_task(101, "factorial", [5])
  # But actually runs on a different machine (port 8001)
  ```
- Python's `xmlrpc` library handles TCP connection, serialization, and response automatically
- Used in real systems: NFS, gRPC, Hadoop

---

### Slide 6 — Load Balancing — Round Robin (60 seconds)

- Tasks distributed evenly across workers
- **How it works:**
  ```
  Task 101 → Worker1
  Task 102 → Worker2
  Task 103 → Worker1
  Task 104 → Worker2
  ```
- `rr_index` pointer advances by 1 after each task
- Wraps around using modulo: `index % number_of_workers`
- **Benefit:** No single worker gets overloaded

---

### Slide 7 — Fault Tolerance (60 seconds)

- **Scenario:** Worker1 crashes mid-execution
- **Detection:** TCP connection timeout (5 seconds) using custom `TimeoutTransport`
- **Recovery:**
  ```
  → Try Worker1  [fails after 5s]
  → Try Worker2  [succeeds]
  → Task COMPLETED
  ```
- Task is **automatically reassigned** — no manual intervention
- If ALL workers fail → status = `FAILED`, graceful error message
- **Benefit:** System stays operational even when nodes go down

---

### Slide 8 — Task Monitoring (45 seconds)

- Every task is tracked in a **task table** (in-memory dictionary on master)
- Task lifecycle:
  ```
  PENDING → RUNNING → COMPLETED
                    → FAILED
  ```
- Client can query:
  - `get_task_status(task_id)` — status of one task
  - `get_all_tasks()` — full table view
- Example output:
  ```
  ID    Status      Worker    Result
  101   COMPLETED   Worker1   120
  102   COMPLETED   Worker2   30
  103   FAILED      —         All workers unavailable
  ```

---

### Slide 9 — Live Demo Highlights (90 seconds)

- **Demo 1:** Submit `factorial(5)` → result 120 on Worker1
- **Demo 2:** Submit 4 tasks → show round-robin alternating Worker1/Worker2
- **Demo 3:** Kill Worker1 → submit task → show 5s pause + reassignment to Worker2
- **Demo 4:** Show task table (`View all tasks`) showing COMPLETED/FAILED history

---

### Slide 10 — Conclusion & Future Scope (60 seconds)

**What we achieved:**
- Functional distributed task execution over RPC
- Round-robin load balancing
- Automatic fault detection and recovery
- Real-time task status monitoring
- Zero external dependencies — pure Python

**Future Scope:**
- Dynamic worker scaling (add workers at runtime)
- Web-based dashboard for monitoring
- Priority-based scheduling
- Cloud deployment (AWS/GCP workers)
- Persistent task history (database storage)

---

## 6. Viva Questions and Answers

---

**Q1. What is RPC and how does it work in your project?**

RPC (Remote Procedure Call) is a protocol that allows a program to execute a function on a remote machine as if calling a local function. In this project, the master calls `execute_task(task_id, task_type, task_data)` on a worker process running on a different port. Python's `xmlrpc.client.ServerProxy` serializes the call to XML, sends it over TCP, and the `xmlrpc.server.SimpleXMLRPCServer` on the worker deserializes it, executes the function, and returns the result as XML. The entire network communication is handled by the library transparently.

---

**Q2. Why did you choose XML-RPC over gRPC?**

We chose XML-RPC because it is built into Python's standard library, requires no external dependencies, and needs no `.proto` schema files. gRPC is more performant and production-grade but requires installing the `grpcio` package, defining Protocol Buffer schemas, and generating stub code — significant overhead for a college project. XML-RPC achieves the same fundamental distributed communication with far simpler setup, making it appropriate for demonstrating the core concepts without complexity.

---

**Q3. How does round-robin load balancing work in your implementation?**

We maintain a shared counter `rr_index` initialized to 0. When a task arrives, the master reads the current index to pick the worker (`WORKERS[rr_index]`), then increments the index using `rr_index = (rr_index + 1) % len(WORKERS)`. The modulo operation ensures the index wraps back to 0 after reaching the last worker. For two workers, this produces the pattern: Task1→Worker1, Task2→Worker2, Task3→Worker1, and so on. A threading lock protects these operations from race conditions when multiple clients submit tasks simultaneously.

---

**Q4. How does fault tolerance work? What happens when a worker crashes?**

When the master calls a worker's RPC method, the call goes through a custom `TimeoutTransport` class that sets a 5-second timeout on the TCP connection. If the worker is down or unresponsive, the connection either refuses immediately or times out after 5 seconds, raising an exception. The master's `submit_task` function catches this exception inside a `for` loop that iterates over all workers. On failure, it logs the error and moves to the next worker in the list. If all workers fail, the task is marked `FAILED` with the message "All workers unavailable" and the client receives this gracefully.

---

**Q5. What are the task states and how does a task transition between them?**

A task has four possible states: `PENDING`, `RUNNING`, `COMPLETED`, and `FAILED`. When first submitted, it is set to `PENDING`. When the master selects a worker and begins the RPC call, it is updated to `RUNNING`. If the worker returns successfully, the status becomes `COMPLETED` with the result stored. If the worker fails and no other worker is available, the status becomes `FAILED`. These states are stored in the master's `task_table` dictionary and can be queried at any time by the client using `get_task_status(task_id)`.

---

**Q6. What is ThreadingMixIn and why did you use it in the master?**

`ThreadingMixIn` is a Python mixin class from the `socketserver` module that makes an XML-RPC server handle each incoming connection in a separate thread. Without it, `SimpleXMLRPCServer` is single-threaded — it processes one client request at a time. If Client A submits a long task and Client B connects while it's running, Client B would be blocked until Client A's task completes. By combining `ThreadingMixIn` with `SimpleXMLRPCServer`, we create `ThreadedXMLRPCServer`, which spawns a new thread for each client connection, allowing multiple simultaneous clients — which is essential for a realistic distributed system.

---

**Q7. What is the difference between centralized and distributed systems? How does your project illustrate this?**

In a centralized system, a single machine handles all computation. If it's overloaded or crashes, the system stops. In a distributed system, work is spread across multiple machines, improving performance, scalability, and reliability. Our project illustrates this difference directly: the master distributes tasks to Worker1 and Worker2 instead of executing them itself. If Worker1 goes down, Worker2 takes over (fault tolerance). If more tasks arrive, adding Worker3 to `config.py` scales the system immediately — without changing any other code.

---

**Q8. How would you add a new task type (e.g., multiplication) to this system?**

Adding a new task type requires changes to only one file — `tasks.py`. You add a new function:
```python
def multiply(args):
    return args[0] * args[1]
```
Then register it in `TASK_HANDLERS`:
```python
TASK_HANDLERS = {"add": add, "factorial": factorial, "reverse": reverse, "multiply": multiply}
```
You also add the corresponding input prompt in `client.py`. The master and worker code require zero changes because they use `TASK_HANDLERS[task_type]` dynamically — this is an example of the **Open/Closed Principle** (open for extension, closed for modification).

---

**Q9. What are the limitations of your current implementation?**

Several limitations exist in the current implementation:
1. **No persistent storage** — task history is lost when the master restarts since `task_table` is in-memory only.
2. **Static worker list** — workers cannot register or deregister dynamically; adding a worker requires editing `config.py` and restarting the master.
3. **Synchronous execution** — the master blocks while waiting for a worker to complete; very long tasks will delay other clients even with threading.
4. **No heartbeat mechanism** — the master only detects worker failure when it tries to assign a task, not proactively in the background.
5. **No authentication** — any process that knows the master's port can submit tasks.

---

**Q10. How is this project related to real-world distributed systems like Hadoop or Kubernetes?**

The core principles are identical. In Apache Hadoop, a JobTracker (master) distributes MapReduce tasks to TaskTrackers (workers) — exactly our master–worker model. Kubernetes' scheduler assigns workload pods to available nodes using resource-aware algorithms analogous to our round-robin strategy. Celery, a Python task queue used in production web applications, uses the same concept of workers pulling tasks from a coordinator and reporting status. Our project is a simplified, transparent implementation of these same architectural patterns — without the production complexity — making the underlying principles clearly visible and understandable.
