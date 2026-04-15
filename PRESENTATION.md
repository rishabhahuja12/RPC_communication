# College Project Presentation — RPC Distributed Task Execution System

---

## 1. Final Academic Project Title

**"Design and Implementation of an Enhanced RPC-Based Distributed Task Execution System with Service Discovery, Auto-Scaling, Round-Robin Load Balancing, Fault Tolerance, Client Isolation, and Role-Based Access Control"**

**Short Title (for slides/report cover):**
*Enhanced RPC-Based Distributed Task Execution System with Service Discovery, Auto-Scaling & Role-Based Access*

---

## 2. Problem Statement

In conventional centralized computing systems, all computational tasks are processed by a single machine, which creates critical limitations in performance, reliability, and scalability. As the volume and complexity of tasks increase, a single machine becomes a bottleneck — slowing execution, exhausting resources, and forming a single point of failure where one crash brings down the entire system. Furthermore, existing distributed frameworks require manual configuration of worker IPs, making scaling tedious and error-prone. Additionally, naïve RPC implementations often violate the core RPC transparency principle by exposing internal system details (worker IPs, task IDs, cluster status) to clients, and fail to isolate client data — allowing one client to view another's tasks and results. This project addresses these limitations by designing a distributed task execution system using XML-RPC, where workers register themselves dynamically through a service discovery registry, a central master node distributes tasks using round-robin load balancing, the system automatically scales workers up or down based on demand, detects and recovers from worker failures using heartbeat monitoring and TCP timeouts, enforces RPC transparency so clients see only computation results without internal details, isolates each client's data using unique client identifiers, and provides a separate admin dashboard for full system monitoring — demonstrating core distributed computing and security principles within a minimal, dependency-free Python environment.

---

## 3. Proposed System Explanation

### Overview

The proposed system follows a **Master–Worker architecture** with a **Service Discovery Registry** over XML-RPC (Remote Procedure Call), implemented entirely in Python using its standard library. The system consists of five logical layers:

1. **Registry Layer** — A service discovery server where workers register themselves and send heartbeats.
2. **Client Layer** — The user submits tasks through a simplified command-line interface that enforces RPC transparency (no internal system details visible).
3. **Master Layer** — A central coordinator that discovers workers from the registry, distributes tasks using round-robin scheduling, tracks their status, handles failures, auto-scales workers, and enforces client isolation.
4. **Worker Layer** — Multiple independent worker processes that self-register, listen for RPC calls, execute assigned tasks, and return results.
5. **Admin Layer** — A separate dashboard for the system operator providing full visibility into tasks, workers, clients, and cluster state.

### Components

| Component | File | Role |
|-----------|------|------|
| Registry | `registry.py` | Service discovery: worker registration, heartbeat monitoring, reaping stale workers |
| Master Node | `master.py` | Task scheduler, load balancer, fault detector, auto-scaler, client isolation enforcer |
| Worker Node | `worker.py` | Self-registering remote task executor (any port, any machine) |
| Client | `client.py` | Simplified user interface — RPC transparent, isolated per client |
| Admin | `admin.py` | Full system monitoring dashboard (master machine only) |
| Task Definitions | `tasks.py` | Implementations of add, factorial, reverse |
| Configuration | `config.py` | Centralized settings: registry/master IPs, ports, timeouts, scaling params |
| Stress Tester | `stress_test.py` | Fires 20 concurrent tasks to test load, discovery, and distribution |

### How It Works

1. The **registry** starts first and listens for worker registrations.
2. **Workers** start on any port, call `registry.register_worker()`, and begin sending heartbeats every 3 seconds.
3. The **master** starts and connects to the registry.
4. The user submits a task (e.g., `factorial(5)`) through `client.py`.
5. The client generates a unique `client_id` (UUID-based) and sends an RPC call to the master at port 9000.
6. The master calls `registry.get_workers()` to discover currently available workers.
7. The master assigns a unique task ID (internal), records the task as `PENDING` with the client_id, and selects a worker using round-robin.
8. The master sends an RPC call (`execute_task(task_id, task_type, task_data)`) to the selected worker.
9. The worker executes the function, returns a result dict with `status: COMPLETED`.
10. The master updates the task table and returns a **sanitized response** to the client — only `{status, result}`, no task ID or worker ID.
11. If the worker is unreachable (timeout after 5 seconds), the master reassigns to the next worker — the client never knows.
12. If no workers are available, the client receives a clean error: "Computation failed."
13. The **admin dashboard** can see all internal details: task IDs, workers, all clients, cluster status.

### Key Features Implemented

- **RPC Transparency:** Client sees only computation results — no task IDs, worker IDs, or cluster internals. The client operates as if processing is happening locally.
- **Client Isolation:** Each client gets a unique UUID-based identity. Clients can only view their own past results — never another client's data.
- **Role-Based Access:** Client has restricted view (inputs → results only); Admin has full system visibility (all tasks, workers, clients, cluster status).
- **Service Discovery:** Workers self-register with the registry — no hardcoded IPs needed.
- **Heartbeat Health Monitoring:** Workers send heartbeats every 3s. The registry removes workers that miss heartbeats for 10s.
- **Auto-Scaling:** A background thread in the master spawns new workers when demand exceeds capacity, or terminates idle workers when demand drops.
- **Round-Robin Load Balancing:** A shared `rr_index` pointer cycles through discovered workers.
- **Fault Tolerance:** `TimeoutTransport` enforces a 5-second TCP deadline. On failure, a retry loop tries the next worker automatically.
- **Graceful Degradation:** If all workers fail, the client receives a clean failure message without crashing.
- **Dynamic Worker Join/Leave:** Start a new worker anytime — it self-registers and begins receiving tasks immediately.
- **Multi-Machine Network Deployment:** All components bind to `0.0.0.0`, accepting connections from any machine on the LAN.
- **Timestamped Logging:** Every log line includes `[HH:MM:SS]`, making fault detection gaps visually measurable.

---

## 4. Related Work Examples

| System | Similarity to This Project |
|--------|---------------------------|
| **Consul / etcd / ZooKeeper** | Service discovery and health checking — our registry serves the same role |
| **Apache Hadoop MapReduce** | Master–worker architecture; a JobTracker distributes tasks to TaskTrackers |
| **Celery (Python Task Queue)** | Distributed task execution with workers; same task assignment and status tracking |
| **Kubernetes (Pod Scheduling + HPA)** | Scheduler assigns workloads (our round-robin), HPA scales replicas (our auto-scaler) |
| **gRPC (Google)** | Modern RPC framework; XML-RPC achieves the same communication model, simpler |
| **OAuth / API Scoping** | Client isolation via client_id mirrors API scoping where users see only their own data |
| **Kubernetes Dashboard / Grafana** | Our admin.py serves the same monitoring role as production admin dashboards |

---

## 5. 10-Minute PPT Slide Structure

---

### Slide 1 — Title Slide (30 seconds)

- **Title:** Enhanced RPC-Based Distributed Task Execution System
- **Subtitle:** With Service Discovery, Auto-Scaling, Load Balancing, Fault Tolerance & Role-Based Access
- Course name, institute name, team member names, date

---

### Slide 2 — Problem Statement (60 seconds)

- Centralized systems: single machine handles all work
- **5 core problems:**
  - High processing load → slow performance
  - Single point of failure → entire system crashes if one machine fails
  - Poor scalability → adding more tasks makes it worse
  - Manual configuration → adding workers requires editing config files and restarting
  - **Security violations** → clients can see internal system details, other clients' data
- **Solution needed:** Distribute work dynamically with security and transparency
- Visual: Single server vs. auto-scaling cluster with client/admin separation

---

### Slide 3 — Objective (30 seconds)

- Design a distributed task execution system using RPC
- Implement **service discovery** so workers register themselves dynamically
- Auto-scale workers based on demand (no manual intervention)
- Handle worker failures automatically (heartbeat + timeout)
- **Enforce RPC transparency** — clients see only inputs and results
- **Isolate client data** — each client sees only their own past results
- **Separate admin access** — full system monitoring only for the operator
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
  (isolated)  [AutoScaler]   ──▶ [Worker2 :8002] ──────┘
                                  [Worker3 :8003] ← auto-spawned
  [Admin] ──▶ [Master :9000]
  (full access, master machine only)
  ```
- Explain each component's role in one line:
  - **Registry:** Service discovery — workers register, master queries (port 7000)
  - **Client:** Submits tasks, sees only results — no internal details (any machine)
  - **Master:** Discovers workers, schedules tasks, auto-scales, enforces isolation (port 9000)
  - **Admin:** Full visibility — all tasks, workers, clients (master machine only)
  - **Workers:** Self-register, execute tasks (any port on any machine)
- Key point: **Client/Admin separation enforces RPC transparency and security**

---

### Slide 5 — What is RPC? + RPC Transparency (60 seconds)

- RPC = Remote Procedure Call
- Lets a program call a function on **another machine** as if it were local
- Example:
  ```
  # Client thinks this is local:
  result = compute("factorial", [5])

  # Actually runs on Worker1 (port 8001) via master (port 9000)
  # Client receives: {"status": "COMPLETED", "result": 120}
  # No task ID, no worker ID — client doesn't know distribution happened
  ```
- **RPC Transparency Principle:** The client should not know RPC is being used
- Our implementation enforces this — client sees only `factorial(5) = 120`
- Admin sees the full picture: Task 101, Worker1, Client_a3f8c2e1

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

### Slide 7 — Security: Client Isolation & Role-Based Access (60 seconds)

- **The Problem (before fix):**
  - Client could see cluster status (worker IPs, auto-scaling)
  - Client could see all task IDs, worker assignments
  - Client could see OTHER clients' tasks and results
  - Violates RPC transparency and data privacy

- **The Fix:**
  - Each client gets a unique UUID: `Client_a3f8c2e1`
  - `submit_task()` returns only `{status, result}` — no IDs
  - `get_my_results()` returns only that client's results
  - Admin dashboard (`admin.py`) has full access — runs on master machine only

- Visual comparison table:
  | | Client sees | Admin sees |
  |---|---|---|
  | Result | `10 + 20 = 30` | Task 101, Worker1, Client_a3f8, 30 |
  | Others' data | Nothing | Everything |

---

### Slide 8 — Fault Tolerance (60 seconds)

- **Two layers of detection:**
  1. **Proactive (heartbeat):** Registry removes dead workers after 10s → master won't try them
  2. **Reactive (timeout):** If worker dies between heartbeats, 5s TCP timeout catches it

- **Recovery visible in master logs:**
  ```
  [10:35:10] Assigning task 105 to Worker1
  [10:35:15] Worker1 unreachable. Trying next...   ← 5s gap
  [10:35:15] Assigning task 105 to Worker2
  [10:35:15] Task 105 → COMPLETED
  ```

- **Client sees nothing wrong** — just gets the result
- If ALL workers fail → client gets "Computation failed" message (no crash)

---

### Slide 9 — Live Demo Highlights (90 seconds)

- **Demo 1:** Submit `factorial(5)` → client shows `factorial(5) = 120` (no task ID, no worker)
- **Demo 2:** Submit 4 tasks → admin shows round-robin: Worker1, Worker2, Worker1, Worker2
- **Demo 3:** Open two clients → submit from each → each sees only own results
- **Demo 4:** Kill Worker1 → submit task → client gets result seamlessly (failover)
- **Demo 5:** Start new worker (`python worker.py 8003`) → admin shows 3 workers immediately
- **Demo 6:** Admin dashboard → view all tasks, cluster status, client summary
- **Demo 7:** Run `stress_test.py` → 20 concurrent tasks complete → admin shows StressTest client

---

### Slide 10 — Conclusion & Future Scope (60 seconds)

**What we achieved:**
- Dynamic service discovery (no hardcoded worker IPs)
- Heartbeat-based health monitoring with automatic reaping
- Auto-scaling workers based on demand
- Round-robin load balancing across discovered workers
- Automatic fault detection and recovery (5s timeout + heartbeat)
- **RPC transparency** — client sees only inputs and results
- **Client isolation** — each client sees only their own data
- **Role-based access** — admin has full visibility, client has restricted view
- **Real multi-machine deployment** across physical machines on a LAN
- Zero external dependencies — pure Python

**Future Scope:**
- Web-based dashboard for monitoring
- Priority-based scheduling
- Cloud deployment (AWS/GCP workers registering remotely)
- Persistent task history (database storage)
- Registry replication (eliminate single point of failure)
- Authentication/encryption for production security

---

## 6. Viva Questions and Answers

---

**Q1. What is RPC and how does it work in your project?**

RPC (Remote Procedure Call) is a protocol that allows a program to execute a function on a remote machine as if calling a local function. In this project, the master calls `execute_task(task_id, task_type, task_data)` on a worker process running on a different port or machine. Python's `xmlrpc.client.ServerProxy` serializes the call to XML, sends it over TCP, and the `xmlrpc.server.SimpleXMLRPCServer` on the worker deserializes it, executes the function, and returns the result as XML. The entire network communication is handled by the library transparently. The client itself only calls `submit_task()` on the master and gets back a clean `{status, result}` — it never communicates with workers directly.

---

**Q2. What is RPC transparency and how do you enforce it?**

RPC transparency means the client should not know that remote processing is happening — it should feel like local computation. We enforce this by: (1) The `submit_task()` function returns only `{status, result}` to the client — no task IDs, no worker IDs, no internal details. (2) The client menu shows only "Compute" and "View past results" — no cluster status or task status options. (3) The client UI displays results in human-readable format like `10 + 20 = 30` rather than showing internal status dictionaries. (4) Error messages say "Computation failed" rather than "Worker1 unreachable". The client literally cannot tell the difference between local and distributed processing.

---

**Q3. How do you isolate client data?**

Each client instance generates a unique identifier on startup using Python's `uuid4` module (e.g., `Client_a3f8c2e1`). This `client_id` is sent with every `submit_task()` call and stored in the master's task table alongside the task data. When a client requests past results via `get_my_results(client_id)`, the master filters the task table and returns only entries matching that specific `client_id`. This means Client A cannot see Client B's tasks or results, even though they share the same master server.

---

**Q4. What is the difference between client.py and admin.py?**

`client.py` is the end-user interface that enforces RPC transparency — it can submit tasks and view only its own past results. It has no access to task IDs, worker IDs, cluster status, or other clients' data. `admin.py` is the system operator's dashboard that runs on the master machine and has full visibility — it can view all tasks from all clients with complete internal details (task IDs, worker assignments, client identifiers), check individual task status by ID, monitor cluster health (active workers, auto-scaling state), and see a summary of all connected clients. This separation mirrors real-world systems where users have restricted access and administrators have full monitoring capabilities.

---

**Q5. What is service discovery and why did you implement it?**

Service discovery is the mechanism by which components in a distributed system find each other without hardcoded addresses. In the original system, worker IPs were listed in `config.py` — adding a new worker required editing this file and restarting the master. With our registry-based service discovery, workers call `register_worker()` on startup and send heartbeats. The master calls `get_workers()` before each task to get the live list. This means you can start a worker on any machine, any port, and it automatically becomes available — no config changes, no restarts. This is similar to how Consul, etcd, and ZooKeeper work in production systems.

---

**Q6. How does the heartbeat mechanism work?**

Each worker runs a background daemon thread that calls `registry.heartbeat(worker_id)` every 3 seconds (configurable via `HEARTBEAT_INTERVAL`). This updates the worker's `last_heartbeat` timestamp in the registry. The registry runs a reaper thread that checks every 5 seconds: if any worker's `last_heartbeat` is older than `HEARTBEAT_TIMEOUT` (10 seconds), the worker is removed from the pool. This provides **proactive** crash detection — the master doesn't have to waste 5 seconds connecting to a dead worker because the registry has already removed it. If the heartbeat returns `False` (registry doesn't recognize the worker), the worker automatically re-registers.

---

**Q7. How does auto-scaling work?**

The master runs a background thread called `auto_scaler_loop()` that checks every 5 seconds. It calculates the ratio of pending/running tasks to active workers. If this ratio exceeds `SCALE_UP_THRESHOLD` (2 tasks per worker), it spawns a new worker process using `subprocess.Popen(["python", "worker.py", <port>])`. The new worker self-registers with the registry and becomes available on the next `get_workers()` call. For scaling down, if a worker has been idle for longer than `SCALE_DOWN_IDLE` (30 seconds) and the worker count exceeds `MIN_WORKERS` (2), the auto-scaler terminates it. Only workers spawned by the auto-scaler can be terminated — manually started workers are never killed.

---

**Q8. Why did you choose XML-RPC over gRPC?**

We chose XML-RPC because it is built into Python's standard library, requires no external dependencies, and needs no `.proto` schema files. gRPC is more performant and production-grade but requires installing the `grpcio` package, defining Protocol Buffer schemas, and generating stub code. XML-RPC achieves the same fundamental distributed communication with far simpler setup, making it appropriate for demonstrating the core concepts without complexity.

---

**Q9. How does round-robin load balancing work with dynamic workers?**

We maintain a shared counter `rr_index` initialized to 0. When a task arrives, the master first fetches the current worker list from the registry using `get_workers()`. It picks the worker at `workers[rr_index % len(workers)]`, then increments the index. Since the worker list is fetched fresh each time, the round-robin naturally adapts: if Worker3 joins, the next cycle includes it; if Worker1 leaves, it's excluded. The modulo operation ensures the index wraps around regardless of how many workers are available.

---

**Q10. How does fault tolerance work? What happens when a worker crashes?**

There are two layers of fault detection. **Layer 1 (Proactive):** The registry's reaper thread checks heartbeats every 5 seconds. If a worker hasn't sent a heartbeat in 10 seconds, it's removed from the pool — the master won't even try to reach it. **Layer 2 (Reactive):** If a worker crashes between heartbeats (within the 10s window), the master's `TimeoutTransport` enforces a 5-second TCP timeout on the connection attempt. The `submit_task` function catches the exception and tries the next worker in the list. If all workers fail, the task is marked `FAILED` with `"Service Unavailable"`. The client sees only "Computation failed" — it has no knowledge of the internal failover process.

---

**Q11. What is ThreadingMixIn and why did you use it?**

`ThreadingMixIn` is a Python mixin class from the `socketserver` module that makes an XML-RPC server handle each incoming connection in a separate thread. Without it, `SimpleXMLRPCServer` processes one request at a time. We use it in both the master (to handle multiple client connections simultaneously) and the registry (to handle concurrent worker registrations and heartbeats). This is essential when the stress test fires 20 tasks at once or when multiple workers are sending heartbeats simultaneously.

---

**Q12. What happens when you say "Service Unavailable"?**

"Service Unavailable" is the internal status stored in the master's task table in two scenarios: (1) when the registry returns an empty worker list, the master immediately marks the task as FAILED; (2) when all registered workers are unreachable after trying each with a 5-second timeout. The **client** never sees this raw message — it only sees "Computation failed. Please try again later." The **admin** can see the full details including the "Service Unavailable" reason. This is similar to HTTP status code 503 in web servers.

---

**Q13. What are the limitations of your current implementation?**

1. **Registry is a single point of failure** — if the registry crashes, new worker discovery stops.
2. **No persistent storage** — task history is lost when the master restarts.
3. **Local auto-scaling only** — the auto-scaler spawns workers on the master's machine only.
4. **Synchronous execution** — the master blocks while waiting for a worker response.
5. **No authentication** — admin endpoints are technically accessible from any machine (though admin.py is intended to run locally).
6. **Single-threaded workers** — each worker handles one task at a time.

---

**Q14. How is this project related to real-world systems?**

The core principles are identical to production systems. **Consul/etcd** provides service discovery and health checks like our registry. **Kubernetes' scheduler** assigns workloads to nodes using strategies like our round-robin. **Kubernetes HPA** auto-scales pods based on metrics like our pending-tasks-per-worker threshold. **Celery** uses the same concept of workers executing tasks from a coordinator. **OAuth/API scoping** enforces data isolation similar to our client_id-based access. **Kubernetes Dashboard/Grafana** provides admin monitoring like our admin.py. Our project is a simplified, transparent implementation of these architectural patterns.

---

**Q15. How would you add a new task type (e.g., multiplication)?**

Adding a new task type requires changes to only two files. In `tasks.py`, add a function and register it:
```python
def multiply(args):
    return args[0] * args[1]

TASK_HANDLERS = {"add": add, "factorial": factorial, "reverse": reverse, "multiply": multiply}
```
Then add the input prompt in `client.py`. The master, registry, admin, and worker code require zero changes because they use `TASK_HANDLERS[task_type]` dynamically — this is an example of the **Open/Closed Principle**.
