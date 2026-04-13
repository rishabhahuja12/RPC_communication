# Project Explanation — RPC Distributed Task Execution System

---

## What This Project Does

This project **implements** a **distributed computing system** where a central machine (master) receives tasks from a user (client) and distributes them to multiple worker machines for execution using **Remote Procedure Calls (RPC)**.

Workers are discovered **dynamically** through a **service discovery registry** — no hardcoded IPs. The system **auto-scales** by spawning or killing worker processes based on demand.

**In simple terms:**
> Instead of one machine doing all the work, the work is split across multiple machines on a real network. Workers register themselves — you don't need to know their IPs in advance. If one machine breaks down, another takes over. If demand spikes, the system spawns new workers automatically. This is how real-world cloud systems like AWS, Google Cloud, and Kubernetes work at a fundamental level.

---

## The Problem It Solves

If a single machine handles everything:
- It gets overloaded under heavy tasks
- If it crashes, everything fails (single point of failure)
- Execution is slow (no parallel work)
- Scaling requires manual configuration changes

This project solves this by introducing:
- **Service discovery** — workers register themselves; master discovers them at runtime
- **Heartbeat monitoring** — registry detects crashed workers automatically
- **Auto-scaling** — master spawns new workers when demand is high, kills idle ones when it drops
- **Multiple workers** to share the load
- **Load balancing** to distribute tasks fairly
- **Fault tolerance** to handle worker crashes
- **Task monitoring** to track what's happening

---

## What is RPC (Remote Procedure Call)?

RPC lets a program call a function that runs on **another machine** as if it were a local function.

### Without RPC (normal local call):
```python
result = factorial(5)   # runs on your machine
```

### With RPC (remote call):
```python
result = worker_proxy.execute_task(101, "factorial", [5])
# This function actually runs on another machine (e.g., port 8001)
# But from the caller's perspective, it looks like a normal function call
```

Python's built-in `xmlrpc` library handles all the networking (TCP, serialization) behind the scenes.

---

## System Architecture

```
                                    ┌──────────────────────┐
                                    │  REGISTRY (PC0)      │
                                    │  0.0.0.0:7000        │
                                    │  Service Discovery   │
                                    │  Heartbeat Monitor   │
                                    └───┬─────────────┬────┘
                                        │             │
                              register/ │             │ get_workers()
                             heartbeat  │             │
                                        │             │
+-----------------------------+         │    +--------┴──────────────+
|  CLIENT (any machine)       |         │    |  MASTER (PC1)         |
|  Connects to MASTER_IP:9000 |────────────▶|  0.0.0.0:9000         |
+-----------------------------+              |  Load Balancer        |
                                             |  Task Tracker         |
                                             |  Fault Detector       |
                                             |  Auto-Scaler          |
                                             +----+-------------+----+
                                                  |             |
                                                  | RPC         | RPC
                                                  v             v
                                           +----------+   +----------+
                                           | WORKER 1 |   | WORKER 2 |
                                           |  (PC2)   |   |  (PC3)   |
                                           | 0.0.0.0  |   | 0.0.0.0  |
                                           | :8001    |   | :8002    |
                                           +----------+   +----------+
                                                ↑               ↑
                                                │  heartbeat    │  heartbeat
                                                └───────────────┘
                                                  every 3 seconds
                                                  to REGISTRY
```

---

## File-by-File Explanation

---

### `config.py` — Configuration

```python
# Master settings (unchanged)
MASTER_IP   = "localhost"
MASTER_PORT = 9000

# Service discovery registry
REGISTRY_IP   = "localhost"
REGISTRY_PORT = 7000

HEARTBEAT_INTERVAL = 3     # workers send heartbeat every 3s
HEARTBEAT_TIMEOUT  = 10    # registry removes worker after 10s silence

WORKER_TIMEOUT = 5         # 5s TCP timeout when master calls a worker

# Auto-scaling
AUTO_SCALE         = True
WORKER_PORT_RANGE  = (8001, 8020)
SCALE_UP_THRESHOLD = 2     # pending tasks per worker before scaling up
SCALE_DOWN_IDLE    = 30    # idle seconds before scaling down
MIN_WORKERS        = 2
MAX_WORKERS        = 6
```

**What it does:**
- Central place to define where the registry and master are running
- **No more hardcoded worker list** — workers register themselves dynamically
- `REGISTRY_IP` is the IP clients/workers use to connect to the registry
- `HEARTBEAT_INTERVAL` controls how often workers ping the registry
- `HEARTBEAT_TIMEOUT` controls how long the registry waits before considering a worker dead
- Auto-scaling settings control when and how the master spawns/kills worker processes
- No logic — pure configuration

---

### `registry.py` — Service Discovery Server (NEW)

**Role:** The single source of truth for which workers are alive. Workers register here; the master queries here.

**RPC methods exposed:**

| Method | Called By | Purpose |
|--------|-----------|---------|
| `register_worker(id, host, port)` | Worker | Add worker to the pool on startup |
| `deregister_worker(id)` | Worker | Remove worker from pool on shutdown |
| `heartbeat(id)` | Worker | Update last-seen timestamp |
| `get_workers()` | Master | Get list of all healthy workers |
| `get_worker_count()` | Master | Quick count for auto-scaler |

**Key data structure:**
```python
worker_pool = {
    "Worker1": {"host": "localhost", "port": 8001, "last_heartbeat": 1713021234.5},
    "Worker2": {"host": "192.168.1.50", "port": 8002, "last_heartbeat": 1713021236.1},
}
```

**Background reaper thread:**
Runs every 5 seconds, checks every worker's `last_heartbeat`. If `current_time - last_heartbeat > HEARTBEAT_TIMEOUT` (10s), the worker is removed from the pool and a log line is printed:
```
[10:35:20] [Registry] ⚠ Reaped Worker1 at localhost:8001 (no heartbeat for 10s)
```

This replaces the old system where worker failures were only detected at task-assignment time (5s timeout). Now, the registry **proactively** removes dead workers, so the master doesn't waste time trying to reach them.

**Why a separate service?**
- Decouples worker discovery from the master — the master doesn't need to know worker IPs at startup
- Multiple masters could share the same registry (future scalability)
- Workers from any machine can join by contacting the registry — no config file changes needed

---

### `worker.py` — Worker Node (Self-Registering)

**Role:** Waits for RPC calls from the master, executes the task, returns the result. Now also **registers with the registry** and **sends heartbeats**.

**How to start:**
```bash
python worker.py 8001                         # local testing
python worker.py 8001 --host 192.168.1.50     # LAN — tells registry your real IP
```

**Lifecycle:**
```
1. Start up
2. Call registry.register_worker("Worker1", "localhost", 8001)
3. Start heartbeat thread (daemon) — sends heartbeat every 3s
4. Listen for RPC calls (execute_task)
5. On Ctrl+C: call registry.deregister_worker("Worker1"), close server
```

**Heartbeat thread:**
```python
def heartbeat_loop():
    while True:
        registry.heartbeat(worker_id)    # update last-seen timestamp
        time.sleep(HEARTBEAT_INTERVAL)   # every 3 seconds
```
If the heartbeat returns `False` (registry doesn't know this worker), the worker automatically re-registers.

**Task execution:** The `execute_task()` function is **completely unchanged** from the original — it still looks up `TASK_HANDLERS[task_type]`, calls the function, and returns the result dict.

---

### `master.py` — Master Node (Dynamic Discovery + Auto-Scaler)

**Role:** The central brain. Discovers workers from the registry at runtime, assigns tasks, tracks status, handles failures, and auto-scales.

**Key changes from the original:**

1. **No more `from config import WORKERS`** — replaced with `fetch_workers()` that queries the registry
2. **Auto-scaler background thread** — spawns/kills worker processes
3. **`get_cluster_status()` RPC method** — lets clients see live cluster info
4. **"Service Unavailable" message** — returned when no workers are available

**Dynamic worker discovery:**
```python
def fetch_workers():
    """Fetch current live worker list from the registry."""
    return get_registry().get_workers()

def submit_task(task_type, task_data):
    workers = fetch_workers()   # ← called EVERY time, not a static list
    if not workers:
        return {"status": "FAILED", "result": "Service Unavailable", ...}
    # ... round-robin over dynamic list ...
```

**The `ts()` helper and why timestamps matter:**
```python
def ts():
    return datetime.now().strftime("%H:%M:%S")
```
Every log line is prefixed with `[HH:MM:SS]`. When a worker fails, the log shows:
```
[10:35:10] Assigning task to Worker1
[10:35:15] Worker1 unreachable. Trying next worker...   ← 5s gap visible
[10:35:15] Assigning task to Worker2
```
The timestamp jump from `:10` to `:15` makes the detection latency measurable and visible — this is the key demo moment for fault tolerance.

---

#### Load Balancing — Round Robin

```python
with lock:
    start_idx = rr_index[0]
    rr_index[0] = (rr_index[0] + 1) % len(workers)  # workers is now dynamic!
```

**How it works:**
```
Task 101: start_idx=0 → assign to workers[0] = Worker1, rr_index becomes 1
Task 102: start_idx=1 → assign to workers[1] = Worker2, rr_index becomes 0
Task 103: start_idx=0 → assign to workers[0] = Worker1, rr_index becomes 1
...and so on
```

`% len(workers)` ensures the index wraps around. Since the worker list is fetched fresh each time, it adapts to workers joining or leaving.

---

#### Fault Tolerance

```python
for i in range(len(workers)):
    worker = workers[(start_idx + i) % len(workers)]
    try:
        proxy = xmlrpc.client.ServerProxy(..., transport=TimeoutTransport(5))
        result = proxy.execute_task(task_id, task_type, task_data)
        return result   # success — exit loop
    except Exception as e:
        print(f"Worker failed. Trying next...")
        # loop continues to next worker
```

**What happens on failure:**
1. Master tries Worker1 → connection refused or no response after 5 seconds → `Exception` raised
2. `except` block catches it → prints warning
3. Loop tries Worker2
4. If Worker2 succeeds → task completed
5. If all workers fail → returns `status: "FAILED"`, `result: "Service Unavailable"`

**Two layers of fault detection:**
1. **Proactive (heartbeat):** Registry removes dead workers after 10s — master won't even try them
2. **Reactive (timeout):** If a worker dies between heartbeats, the 5s TCP timeout catches it at task time

---

#### Auto-Scaler

```python
def auto_scaler_loop():
    while True:
        time.sleep(5)
        workers = fetch_workers()
        pending = count_pending_tasks()

        # Scale UP if too many pending tasks per worker
        if pending / worker_count > SCALE_UP_THRESHOLD:
            subprocess.Popen(["python", "worker.py", str(next_port)])

        # Scale DOWN if worker is idle too long
        if worker_idle_time > SCALE_DOWN_IDLE and worker_count > MIN_WORKERS:
            process.terminate()

        # Always maintain MIN_WORKERS
        if worker_count < MIN_WORKERS:
            spawn enough workers to reach MIN_WORKERS
```

**How scaling works:**
1. Every 5 seconds, the auto-scaler checks the ratio of pending tasks to workers
2. If `pending / workers > 2` (threshold), it spawns a new worker using `subprocess.Popen`
3. The new worker self-registers with the registry via heartbeat
4. The master finds it on the next `fetch_workers()` call
5. If demand drops and a spawned worker is idle for 30s, it's terminated
6. Only workers spawned by the auto-scaler are eligible for termination (manually started workers are never killed)

---

#### Threaded Server

```python
class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass
```

Without `ThreadingMixIn`, the master can only handle one client at a time (blocking).
With it, each incoming client request runs in its own thread — multiple clients can submit tasks simultaneously.

---

#### Task Lifecycle in the Master:

```
submit_task() called
      ↓
task_id = 101, status = "PENDING"
      ↓
fetch_workers() from registry
      ↓
No workers? → FAILED: "Service Unavailable"
      ↓
Round-robin picks Worker1
      ↓
status = "RUNNING", worker = "Worker1"
      ↓
RPC call to Worker1
      ↓
Success?  → status = "COMPLETED", result = 120
Failure?  → Try Worker2
              Success? → status = "COMPLETED"
              Failure? → status = "FAILED", result = "Service Unavailable"
```

---

### `client.py` — Client

**Role:** The user interface. Lets you submit tasks, check status, view all tasks, and **view cluster status**. Communicates with the master via XML-RPC.

```python
master = xmlrpc.client.ServerProxy(f"http://{MASTER_IP}:{MASTER_PORT}/", allow_none=True)
result = master.submit_task("factorial", [5])
```

**Menu options:**
- **Option 1 (Submit task):** Takes task type and arguments from user, sends to master
- **Option 2 (Check task status):** Queries master for a specific task ID
- **Option 3 (View all tasks):** Gets entire task table from master and displays it
- **Option 4 (View cluster status):** Shows active workers, task counts, auto-scaler state
- **Option 5 (Exit):** Quits the client (master and workers keep running)

**Cluster status output example:**
```
  ── Cluster Status ──
  Active workers : 3
    • Worker1@localhost:8001
    • Worker2@localhost:8002
    • Worker3@localhost:8003
  Pending tasks  : 0
  Running tasks  : 0
  Completed      : 15
  Failed         : 0
  Auto-scaling   : ON (2-6)
  Auto-spawned   : Worker3
```

---

### `stress_test.py` — Stress Tester

**Role:** Fires 20 tasks simultaneously from one machine to test the system under concurrent load.

```python
threads = [threading.Thread(target=submit, args=(i,)) for i in range(NUM_TASKS)]
for t in threads: t.start()
for t in threads: t.join()
```

**How it works:**
1. Creates 20 threads, each pointing to a different task number
2. All threads start at almost the same time (`t.start()` in a loop)
3. Each thread creates its own `ServerProxy` connection to the master and calls `submit_task()`
4. The master, being threaded (`ThreadingMixIn`), handles all 20 connections simultaneously
5. Round-robin distributes them across all discovered workers
6. After all threads finish (`t.join()`), prints a summary with per-worker bar chart and **unique worker count**

**Why a new `ServerProxy` per thread?**
`ServerProxy` is not thread-safe — sharing one proxy between 20 threads causes race conditions. Each thread gets its own connection.

---

## Data Flow — End to End

Here's what happens when you type `factorial(5)`:

```
1. client.py  (any machine on LAN)
   User picks "1. Submit task", type=factorial, number=5
   Calls: master_proxy.submit_task("factorial", [5])
   ↓ (XML-RPC over TCP to MASTER_IP:9000)

2. master.py — submit_task()  (PC1 - master machine)
   Assigns task_id = 101
   Sets task_table[101] = {status: "PENDING", worker: None, result: None}
   Calls: registry_proxy.get_workers()
   ↓ (XML-RPC to REGISTRY_IP:7000)

3. registry.py — get_workers()
   Returns: [{id: "Worker1", host: "localhost", port: 8001},
             {id: "Worker2", host: "localhost", port: 8002}]
   ↑ (response back to master)

4. master.py — back in submit_task()
   Round-robin picks Worker1 (rr_index=0)
   Sets task_table[101]["status"] = "RUNNING"
   Calls: worker_proxy.execute_task(101, "factorial", [5])
   ↓ (XML-RPC over TCP to Worker1_IP:8001)

5. worker.py — execute_task()  (PC2 - Worker1 machine)
   Looks up TASK_HANDLERS["factorial"]
   Calls: factorial([5]) = math.factorial(5) = 120
   Returns: {taskID: 101, status: "COMPLETED", result: 120, workerID: "Worker1"}
   ↑ (XML-RPC response back to master over LAN)

6. master.py — back in submit_task()
   Updates task_table[101] = {status: "COMPLETED", worker: "Worker1", result: 120}
   Returns result dict to client
   ↑ (XML-RPC response back to client over LAN)

7. client.py
   Receives result dict
   Prints: Task ID: 101, Status: COMPLETED, Result: 120, Worker: Worker1
```

---

## Key Concepts Summary

| Concept | Where It Is | How It Works |
|---------|------------|--------------|
| RPC | All files | `xmlrpc.server` + `xmlrpc.client` handle network calls |
| Service Discovery | `registry.py` | Workers register/heartbeat; master calls `get_workers()` |
| Heartbeat | `worker.py` → `registry.py` | Workers ping registry every 3s; stale workers reaped after 10s |
| Auto-Scaling | `master.py` | Background thread spawns/kills workers based on demand |
| Load Balancing | `master.py:rr_index` | Cycles through discovered workers 0→1→2→0→1→2 |
| Fault Tolerance | `master.py:for loop` | Catches exceptions, tries next worker |
| Timeout | `master.py:TimeoutTransport` | TCP connection limit of 5 seconds |
| Task Monitoring | `master.py:task_table` | Dict tracking every task's lifecycle |
| Task States | `master.py` | PENDING → RUNNING → COMPLETED/FAILED |
| Threading | `master.py:ThreadedXMLRPCServer` | Each client request in its own thread |
| Multi-Machine Binding | `worker.py` + `master.py` + `registry.py` | Bind to `0.0.0.0` — accept from any LAN machine |
| Network Config | `config.py` | Registry IP, Master IP — no worker IPs needed |
| Timestamped Logging | All files: `ts()` | `[HH:MM:SS]` on every log — makes 5s fault detection gap measurable |
| Stress Testing | `stress_test.py` | 20 threads fire concurrent tasks, shows distribution |

---

## Why Each File Exists Separately

| File | Reason for Separation |
|------|----------------------|
| `config.py` | Change IPs/ports/scaling params without touching logic |
| `tasks.py` | Add new task types without touching network code |
| `registry.py` | Decoupled service discovery — can run on any machine |
| `worker.py` | Run multiple copies independently on different machines and ports |
| `master.py` | Single central coordinator — never run multiple copies |
| `client.py` | User-facing — can be run by multiple users on any machine simultaneously |
| `stress_test.py` | Standalone load tester — run from any machine, independent of client |

---

## What Would Break If You Changed Something

| Change | What Breaks |
|--------|------------|
| `REGISTRY_IP` in config.py ≠ registry machine's actual IP | Workers can't register; master can't discover workers |
| `MASTER_IP` in config.py ≠ master machine's actual IP | Client/stress_test can't connect to master |
| Registry not started before workers | Workers log warning but keep retrying via heartbeat thread |
| Registry crashes after workers registered | Master uses last-known worker list until it re-queries |
| Worker bound to `"localhost"` instead of `"0.0.0.0"` | Only accepts connections from same machine |
| Task function raises unhandled exception | Worker returns FAILED (caught by try/except) |
| All workers down | Client sees "Service Unavailable" |
| Master down | Client throws ConnectionRefusedError immediately |
| `WORKER_TIMEOUT` too low (e.g., 0.1s) | Tasks fail even when workers are alive |
| `HEARTBEAT_TIMEOUT` too low (e.g., 1s) | Workers get reaped between heartbeats |
| Firewall blocking ports 7000/8001/8002/9000 | Remote machines can't connect |

---

## Real-World Equivalents

This project is a simplified version of how these real systems work:

| Real System | Our Equivalent |
|-------------|----------------|
| Consul / etcd / ZooKeeper | Registry — service discovery and health checks |
| Kubernetes Pod Scheduling | Master's round-robin + auto-scaling logic |
| AWS Lambda / Cloud Functions | Worker nodes executing tasks |
| Kubernetes HPA (Horizontal Pod Autoscaler) | Auto-scaler spawning/killing workers based on demand |
| Circuit Breaker pattern | Fault tolerance + timeout |
| Task Queue (Celery, RabbitMQ) | task_table + PENDING/RUNNING states |
| gRPC (production-grade) | XML-RPC (our simpler version) |
