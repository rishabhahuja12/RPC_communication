# College Project Presentation — RPC Distributed Task Execution System

---

## 1. Final Academic Project Title

**"Design and Implementation of an Enhanced RPC-Based Distributed Task Execution System with Service Discovery, Auto-Scaling, Round-Robin Load Balancing, Fault Tolerance, and Real-Time Task Monitoring"**

**Short Title (for slides/report cover):**
*Enhanced RPC-Based Distributed Task Execution System with Service Discovery & Auto-Scaling*

---

## 2. Problem Statement

In conventional centralized computing systems, all computational tasks are processed by a single machine, which creates critical limitations in performance, reliability, and scalability. As the volume and complexity of tasks increase, a single machine becomes a bottleneck — slowing execution, exhausting resources, and forming a single point of failure where one crash brings down the entire system. Furthermore, existing distributed frameworks require manual configuration of worker IPs, making scaling tedious and error-prone. This project addresses these limitations by designing a distributed task execution system using XML-RPC, where workers register themselves dynamically through a service discovery registry, a central master node distributes tasks using round-robin load balancing, the system automatically scales workers up or down based on demand, detects and recovers from worker failures using heartbeat monitoring and TCP timeouts, and maintains a real-time task status tracking table — demonstrating core distributed computing principles within a minimal, dependency-free Python environment.

---

## 3. Proposed System Explanation

### Overview

The proposed system follows a **Master–Worker architecture** with a **Service Discovery Registry** over XML-RPC (Remote Procedure Call), implemented entirely in Python using its standard library. The system consists of four logical layers:

1. **Registry Layer** — A service discovery server where workers register themselves and send heartbeats.
2. **Client Layer** — The user submits tasks through an interactive command-line interface.
3. **Master Layer** — A central coordinator that discovers workers from the registry, distributes tasks using round-robin scheduling, tracks their status, handles failures, and auto-scales workers.
4. **Worker Layer** — Multiple independent worker processes that self-register, listen for RPC calls, execute assigned tasks, and return results.

### Components

| Component | File | Role |
|-----------|------|------|
| Registry | `registry.py` | Service discovery: worker registration, heartbeat monitoring, reaping stale workers |
| Master Node | `master.py` | Task scheduler, load balancer, fault detector, auto-scaler |
| Worker Node | `worker.py` | Self-registering remote task executor (any port, any machine) |
| Client | `client.py` | User interface for task submission, monitoring, and cluster status |
| Task Definitions | `tasks.py` | Implementations of add, factorial, reverse |
| Configuration | `config.py` | Centralized settings: registry/master IPs, ports, timeouts, scaling params |
| Stress Tester | `stress_test.py` | Fires 20 concurrent tasks to test load, discovery, and distribution |

### How It Works

1. The **registry** starts first and listens for worker registrations.
2. **Workers** start on any port, call `registry.register_worker()`, and begin sending heartbeats every 3 seconds.
3. The **master** starts and connects to the registry.
4. The user submits a task (e.g., `factorial(5)`) through `client.py`.
5. The client sends an RPC call to the master at port 9000.
6. The master calls `registry.get_workers()` to discover currently available workers.
7. The master assigns a unique task ID, records the task as `PENDING`, and selects a worker using round-robin.
8. The master sends an RPC call (`execute_task(task_id, task_type, task_data)`) to the selected worker.
9. The worker executes the function, returns a result dict with `status: COMPLETED`.
10. The master updates the task table to `COMPLETED` and forwards the result to the client.
11. If the worker is unreachable (timeout after 5 seconds), the master reassigns to the next worker.
12. If no workers are available, the client receives `"Service Unavailable"`.

### Key Features Implemented

- **Service Discovery:** Workers self-register with the registry — no hardcoded IPs needed. The master discovers workers dynamically at runtime.
- **Heartbeat Health Monitoring:** Workers send heartbeats every 3s. The registry's reaper thread removes workers that miss heartbeats for 10s, enabling proactive crash detection.
- **Auto-Scaling:** A background thread in the master monitors pending tasks and automatically spawns new workers (via `subprocess`) when demand exceeds capacity, or terminates idle workers when demand drops. Configurable min/max bounds.
- **Round-Robin Load Balancing:** A shared `rr_index` pointer cycles through discovered workers, ensuring equal task distribution.
- **Fault Tolerance:** A `TimeoutTransport` class enforces a 5-second TCP deadline on each worker call. On failure, a retry loop tries the next worker automatically.
- **Real-Time Task Monitoring:** `task_table` dictionary tracks every task through states: `PENDING → RUNNING → COMPLETED / FAILED`.
- **Cluster Status View:** Client can view live worker count, auto-scaler state, and task statistics.
- **Concurrent Client Handling:** `ThreadingMixIn` enables the master to serve multiple client connections simultaneously.
- **Graceful Degradation:** If all workers fail, the system returns `"Service Unavailable"` without crashing.
- **Dynamic Worker Join/Leave:** Start a new worker anytime — it self-registers and begins receiving tasks immediately. No restart needed.
- **Multi-Machine Network Deployment:** All components bind to `0.0.0.0`, accepting connections from any machine on the LAN.
- **Timestamped Logging:** Every log line includes `[HH:MM:SS]`, making the fault detection gap visually measurable during demos.

---

## 4. Related Work Examples

| System | Similarity to This Project |
|--------|---------------------------|
| **Consul / etcd / ZooKeeper** | Service discovery and health checking — our registry serves the same fundamental role: workers register, master discovers |
| **Apache Hadoop MapReduce** | Master–worker architecture; a JobTracker distributes tasks to TaskTrackers, same as our master distributing tasks to workers |
| **Celery (Python Task Queue)** | Distributed task execution with workers; uses a broker instead of direct RPC, but task assignment and status tracking are identical |
| **Kubernetes (Pod Scheduling + HPA)** | The scheduler assigns workloads to nodes (our round-robin), and the Horizontal Pod Autoscaler scales replicas based on demand (our auto-scaler) |
| **gRPC (Google)** | Modern high-performance RPC framework; this project uses XML-RPC as a simpler alternative achieving the same communication model |
| **BOINC (Volunteer Computing)** | Distributes scientific tasks to volunteer machines — conceptually identical to our workers receiving and executing tasks |

---

## 5. 10-Minute PPT Slide Structure

---

### Slide 1 — Title Slide (30 seconds)

- **Title:** Enhanced RPC-Based Distributed Task Execution System
- **Subtitle:** With Service Discovery, Auto-Scaling, Load Balancing, and Fault Tolerance
- Course name, institute name, team member names, date

---

### Slide 2 — Problem Statement (60 seconds)

- Centralized systems: single machine handles all work
- **4 core problems:**
  - High processing load → slow performance
  - Single point of failure → entire system crashes if one machine fails
  - Poor scalability → adding more tasks makes it worse
  - Manual configuration → adding workers requires editing config files and restarting
- **Solution needed:** Distribute work dynamically across self-discovering machines
- Visual: Single server vs. auto-scaling cluster

---

### Slide 3 — Objective (30 seconds)

- Design a distributed task execution system using RPC
- Implement **service discovery** so workers register themselves dynamically
- Auto-scale workers based on demand (no manual intervention)
- Handle worker failures automatically (heartbeat + timeout)
- Track task status in real time
- Deploy across **real physical machines** on a LAN network
- Keep it lightweight — no external dependencies (pure Python)

---

### Slide 4 — System Architecture (90 seconds)

- Show the architecture diagram:
  ```
                          ┌────────────┐
                          │  REGISTRY  │ :7000
                          │  Service   │
                     ┌───▶│  Discovery │◀── heartbeat ──┐
                     │    └────────────┘                │
                     │         ▲                        │
               get_workers()  │ register                │
                     │        │                         │
  [Client]──▶ [Master :9000] ──▶ [Worker1 :8001]       │
              [AutoScaler]   ──▶ [Worker2 :8002] ──────┘
                                  [Worker3 :8003] ← spawned by auto-scaler
  ```
- Explain each component's role in one line:
  - **Registry:** Service discovery — workers register, master queries (port 7000)
  - **Client:** Submits tasks, views results (any machine)
  - **Master:** Discovers workers, schedules tasks, auto-scales (port 9000)
  - **Workers:** Self-register, execute tasks (any port on any machine)
- Key point: **No hardcoded worker IPs** — workers announce themselves

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

### Slide 6 — Service Discovery & Auto-Scaling (90 seconds)

- **Service Discovery:**
  - Workers call `registry.register_worker()` on startup
  - Workers send `heartbeat()` every 3 seconds
  - Registry reaps workers that miss heartbeats for 10 seconds
  - Master calls `registry.get_workers()` before each task assignment
  - **Result:** No hardcoded IPs. Start a worker anywhere — it just works.

- **Auto-Scaling:**
  - Master monitors: `pending_tasks / worker_count`
  - If ratio > threshold → spawn new worker via `subprocess`
  - If worker idle > 30s and above minimum → terminate
  - Bounds: MIN_WORKERS=2, MAX_WORKERS=6
  - **Result:** System adapts to load automatically

---

### Slide 7 — Load Balancing — Round Robin (45 seconds)

- Tasks distributed evenly across discovered workers
- **How it works:**
  ```
  Task 101 → Worker1
  Task 102 → Worker2
  Task 103 → Worker3
  Task 104 → Worker1
  ```
- `rr_index` pointer advances by 1 after each task
- Wraps around using modulo: `index % number_of_workers`
- Worker list is **dynamic** — adapts as workers join/leave

---

### Slide 8 — Fault Tolerance (60 seconds)

- **Two layers of detection:**
  1. **Proactive (heartbeat):** Registry removes dead workers after 10s → master won't try them
  2. **Reactive (timeout):** If worker dies between heartbeats, 5s TCP timeout catches it

- **Recovery visible in timestamped logs:**
  ```
  [10:35:10] Assigning task 105 to Worker1
  [10:35:15] Worker1 unreachable. Trying next...   ← 5s gap
  [10:35:15] Assigning task 105 to Worker2
  [10:35:15] Task 105 → COMPLETED
  ```

- If ALL workers fail → **"Service Unavailable"** returned to client
- Auto-scaler detects 0 workers and spawns new ones

---

### Slide 9 — Live Demo Highlights (90 seconds)

- **Demo 1:** Submit `factorial(5)` → result 120 on Worker1
- **Demo 2:** Submit 4 tasks → show round-robin alternating workers
- **Demo 3:** Kill Worker1 → submit task → show reassignment (with or without 5s gap depending on Ctrl+C vs force kill)
- **Demo 4:** Start a new worker mid-session (`python worker.py 8003`) → submit task → it goes to Worker3. Say: *"No config change, no restart — the worker registered itself automatically."*
- **Demo 5:** Kill all workers → submit task → show **"Service Unavailable"** message
- **Demo 6:** View cluster status (Option 4) → show live worker list and auto-scaler state
- **Demo 7:** Run `stress_test.py` → 20 concurrent tasks → even distribution bar chart

---

### Slide 10 — Conclusion & Future Scope (60 seconds)

**What we achieved:**
- Dynamic service discovery (no hardcoded worker IPs)
- Heartbeat-based health monitoring with automatic reaping
- Auto-scaling workers based on demand
- Round-robin load balancing across discovered workers
- Automatic fault detection and recovery (5s timeout + heartbeat)
- "Service Unavailable" graceful error when all workers down
- Real-time task status monitoring and cluster status view
- **Real multi-machine deployment** across physical machines on a LAN
- Zero external dependencies — pure Python

**Future Scope:**
- Web-based dashboard for monitoring
- Priority-based scheduling
- Cloud deployment (AWS/GCP workers registering remotely)
- Persistent task history (database storage)
- Registry replication (eliminate single point of failure)

---

## 6. Viva Questions and Answers

---

**Q1. What is RPC and how does it work in your project?**

RPC (Remote Procedure Call) is a protocol that allows a program to execute a function on a remote machine as if calling a local function. In this project, the master calls `execute_task(task_id, task_type, task_data)` on a worker process running on a different port. Python's `xmlrpc.client.ServerProxy` serializes the call to XML, sends it over TCP, and the `xmlrpc.server.SimpleXMLRPCServer` on the worker deserializes it, executes the function, and returns the result as XML. The entire network communication is handled by the library transparently.

---

**Q2. What is service discovery and why did you implement it?**

Service discovery is the mechanism by which components in a distributed system find each other without hardcoded addresses. In the original system, worker IPs were listed in `config.py` — adding a new worker required editing this file and restarting the master. With our registry-based service discovery, workers call `register_worker()` on startup and send heartbeats. The master calls `get_workers()` before each task to get the live list. This means you can start a worker on any machine, any port, and it automatically becomes available — no config changes, no restarts. This is similar to how Consul, etcd, and ZooKeeper work in production systems.

---

**Q3. How does the heartbeat mechanism work?**

Each worker runs a background daemon thread that calls `registry.heartbeat(worker_id)` every 3 seconds (configurable via `HEARTBEAT_INTERVAL`). This updates the worker's `last_heartbeat` timestamp in the registry. The registry runs a reaper thread that checks every 5 seconds: if any worker's `last_heartbeat` is older than `HEARTBEAT_TIMEOUT` (10 seconds), the worker is removed from the pool. This provides **proactive** crash detection — the master doesn't have to waste 5 seconds connecting to a dead worker because the registry has already removed it. If the heartbeat returns `False` (registry doesn't recognize the worker), the worker automatically re-registers.

---

**Q4. How does auto-scaling work?**

The master runs a background thread called `auto_scaler_loop()` that checks every 5 seconds. It calculates the ratio of pending/running tasks to active workers. If this ratio exceeds `SCALE_UP_THRESHOLD` (2 tasks per worker), it spawns a new worker process using `subprocess.Popen(["python", "worker.py", <port>])`. The new worker self-registers with the registry and becomes available on the next `get_workers()` call. For scaling down, if a worker has been idle for longer than `SCALE_DOWN_IDLE` (30 seconds) and the worker count exceeds `MIN_WORKERS` (2), the auto-scaler terminates it. Only workers spawned by the auto-scaler can be terminated — manually started workers are never killed.

---

**Q5. Why did you choose XML-RPC over gRPC?**

We chose XML-RPC because it is built into Python's standard library, requires no external dependencies, and needs no `.proto` schema files. gRPC is more performant and production-grade but requires installing the `grpcio` package, defining Protocol Buffer schemas, and generating stub code. XML-RPC achieves the same fundamental distributed communication with far simpler setup, making it appropriate for demonstrating the core concepts without complexity.

---

**Q6. How does round-robin load balancing work with dynamic workers?**

We maintain a shared counter `rr_index` initialized to 0. When a task arrives, the master first fetches the current worker list from the registry using `get_workers()`. It picks the worker at `workers[rr_index % len(workers)]`, then increments the index. Since the worker list is fetched fresh each time, the round-robin naturally adapts: if Worker3 joins, the next cycle includes it; if Worker1 leaves, it's excluded. The modulo operation ensures the index wraps around regardless of how many workers are available.

---

**Q7. How does fault tolerance work? What happens when a worker crashes?**

There are two layers of fault detection. **Layer 1 (Proactive):** The registry's reaper thread checks heartbeats every 5 seconds. If a worker hasn't sent a heartbeat in 10 seconds, it's removed from the pool — the master won't even try to reach it. **Layer 2 (Reactive):** If a worker crashes between heartbeats (within the 10s window), the master's `TimeoutTransport` enforces a 5-second TCP timeout on the connection attempt. The `submit_task` function catches the exception and tries the next worker in the list. If all workers fail, the task is marked `FAILED` with `"Service Unavailable"`. The timestamped logs make this detection visible — a 5-second timestamp gap shows exactly when the failure was detected.

---

**Q8. What is ThreadingMixIn and why did you use it?**

`ThreadingMixIn` is a Python mixin class from the `socketserver` module that makes an XML-RPC server handle each incoming connection in a separate thread. Without it, `SimpleXMLRPCServer` processes one request at a time. We use it in both the master (to handle multiple client connections simultaneously) and the registry (to handle concurrent worker registrations and heartbeats). This is essential when the stress test fires 20 tasks at once or when multiple workers are sending heartbeats simultaneously.

---

**Q9. What happens when you say "Service Unavailable"?**

"Service Unavailable" is returned to the client in two scenarios: (1) when the registry returns an empty worker list (zero workers registered), the master skips the retry loop entirely and immediately returns FAILED with this message; (2) when all registered workers are unreachable (after trying each with a 5-second timeout), the result is the same. This is similar to HTTP status code 503 in web servers. The system doesn't crash — the client receives a clear error, and as soon as workers become available again (either by restarting them or via auto-scaler), subsequent tasks succeed.

---

**Q10. What are the limitations of your current implementation?**

1. **Registry is a single point of failure** — if the registry crashes, new worker discovery stops (existing connections keep working until a re-query).
2. **No persistent storage** — task history is lost when the master restarts.
3. **Local auto-scaling only** — the auto-scaler spawns workers on the master's machine via subprocess; it cannot start workers on remote machines.
4. **Synchronous execution** — the master blocks while waiting for a worker response.
5. **No authentication** — any machine on the network can register as a worker or submit tasks.
6. **Single-threaded workers** — each worker handles one task at a time.

---

**Q11. How is this project related to real-world systems?**

The core principles are identical to production systems. **Consul/etcd** provides service discovery and health checks like our registry. **Kubernetes' scheduler** assigns workloads to nodes using strategies like our round-robin. **Kubernetes HPA** auto-scales pods based on metrics like our pending-tasks-per-worker threshold. **Celery** uses the same concept of workers executing tasks from a coordinator. Our project is a simplified, transparent implementation of these architectural patterns — making the underlying principles clearly visible.

---

**Q12. How would you add a new task type (e.g., multiplication)?**

Adding a new task type requires changes to only one file — `tasks.py`. Add a function and register it:
```python
def multiply(args):
    return args[0] * args[1]

TASK_HANDLERS = {"add": add, "factorial": factorial, "reverse": reverse, "multiply": multiply}
```
Then add the input prompt in `client.py`. The master, registry, and worker code require zero changes because they use `TASK_HANDLERS[task_type]` dynamically — this is an example of the **Open/Closed Principle**.
