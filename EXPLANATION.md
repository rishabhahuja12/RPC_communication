# Project Explanation — RPC Distributed Task Execution System

---

## What This Project Does

This project **implements** a **distributed computing system** where a central machine (master) receives tasks from a user (client) and distributes them to multiple worker machines for execution using **Remote Procedure Calls (RPC)**.

**In simple terms:**
> Instead of one machine doing all the work, the work is split across multiple machines on a real network. If one machine breaks down, another takes over. This is how real-world cloud systems like AWS, Google Cloud, and Hadoop work at a fundamental level.

---

## The Problem It Solves

If a single machine handles everything:
- It gets overloaded under heavy tasks
- If it crashes, everything fails (single point of failure)
- Execution is slow (no parallel work)

This project solves this by introducing:
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
+-----------------------------+
|  CLIENT (any machine)       |   ← You interact here (client.py)
|  Connects to MASTER_IP:9000 |
+----------+------------------+
           |
           | RPC call over LAN
           v
+-----------------------------+
|  MASTER (PC1)               |   ← Brain of the system (master.py)
|  Binds to 0.0.0.0:9000      |   ← Accepts from any machine
|  Load Balancer              |   ← Decides which worker gets the task
|  Task Tracker               |   ← Keeps record of all tasks
|  Fault Detector             |   ← Detects unresponsive workers
+----+-------------------+----+
     |                   |
     | RPC over LAN      | RPC over LAN
     v                   v
+----------+       +----------+
| WORKER 1 |       | WORKER 2 |   ← Do the actual computation
|  (PC2)   |       |  (PC3)   |   ← (worker.py)
| 0.0.0.0  |       | 0.0.0.0  |
| :8001    |       | :8002    |
+----------+       +----------+
```

---

## File-by-File Explanation

---

### `config.py` — Configuration

```python
# IP of the machine running master.py (used by clients to connect)
MASTER_IP   = "localhost"       # ← replace with master machine's LAN IP
MASTER_PORT = 9000

WORKERS = [
    {"id": "Worker1", "host": "localhost", "port": 8001},  # ← replace with Worker1's LAN IP
    {"id": "Worker2", "host": "localhost", "port": 8002},  # ← replace with Worker2's LAN IP
]
WORKER_TIMEOUT = 5
```

**What it does:**
- Central place to define where workers and master are running
- `MASTER_IP` is the IP clients use to **connect to** the master — set to the master machine's LAN IP for multi-machine use
- `WORKERS[x]["host"]` is each worker's LAN IP — the master uses these to **connect to** workers
- Servers bind to `0.0.0.0` (all interfaces) — IPs here are only for outbound connections
- `WORKER_TIMEOUT = 5` means: if a worker doesn't reply in 5 seconds, it's considered failed
- To add a 3rd worker, add `{"id": "Worker3", "host": "<PC4-IP>", "port": 8003}` here
- No logic — pure configuration

---

### `tasks.py` — Task Definitions

```python
def add(args):      return args[0] + args[1]
def factorial(args): return math.factorial(args[0])
def reverse(args):  return args[0][::-1]

TASK_HANDLERS = {"add": add, "factorial": factorial, "reverse": reverse}
```

**What it does:**
- Defines what each task type actually computes
- `TASK_HANDLERS` is a dictionary that maps a task name (string) to a function
- When a worker receives `task_type = "factorial"`, it looks up `TASK_HANDLERS["factorial"]` and calls it
- Adding new task types is simple — just add a function and register it in `TASK_HANDLERS`

**Why `args` is a list?**
XML-RPC transmits data as lists. `args[0]` is the first argument, `args[1]` is the second, etc.

---

### `worker.py` — Worker Node

**Role:** Waits for RPC calls from the master, executes the task, returns the result.

**How to start:**
```bash
python worker.py 8001   # starts Worker1
python worker.py 8002   # starts Worker2
```

**Core function:**
```python
def execute_task(task_id, task_type, task_data):
    result = TASK_HANDLERS[task_type](task_data)
    return {"taskID": task_id, "status": "COMPLETED", "result": result, "workerID": worker_id}
```

**Step-by-step what happens when a task arrives:**
1. Worker receives: `execute_task(101, "factorial", [5])`
2. Looks up `TASK_HANDLERS["factorial"]` → finds the `factorial` function
3. Calls `factorial([5])` → returns `120`
4. Wraps result in a dict: `{"taskID": 101, "status": "COMPLETED", "result": 120, "workerID": "Worker1"}`
5. Sends dict back to master over XML-RPC

**What if the task type is unknown or throws an error?**
- Unknown type: returns `status: "FAILED"` with an error message
- Runtime error (e.g., factorial of -1): caught by `try/except`, returns `status: "FAILED"`

**The server part:**
```python
def ts():
    return datetime.now().strftime("%H:%M:%S")

server = SimpleXMLRPCServer(("0.0.0.0", port), ...)
server.register_function(execute_task, "execute_task")
try:
    server.serve_forever()
except KeyboardInterrupt:
    print(f"\n[{ts()}] [{worker_id}] Shutting down.")
    server.server_close()
```
- `ts()` returns the current time as a string (e.g. `10:35:15`) — prepended to every log line
- Binds to `0.0.0.0` — listens on **all** network interfaces, accepting connections from any machine on the LAN (not just localhost)
- Registers `execute_task` as the callable RPC method
- `KeyboardInterrupt` (Ctrl+C) is caught cleanly — prints "Shutting down." and releases the port so it can be restarted immediately

---

### `master.py` — Master Node

**Role:** The central brain. Receives tasks from clients, assigns them to workers, tracks status, handles failures.

**Key data structures:**
```python
task_table = {}       # {101: {status: "COMPLETED", worker: "Worker1", result: 120}}
task_counter = [100]  # starts at 100, increments to 101, 102, 103...
rr_index = [0]        # round-robin pointer: 0=Worker1, 1=Worker2, 0=Worker1...
```

**Why lists `[100]` instead of plain integers?**
Python integers are immutable — you can't modify them inside a function with just `=`. Using a single-element list `[0]` lets multiple threads share and update the value safely.

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
start_idx = rr_index[0]
rr_index[0] = (rr_index[0] + 1) % len(WORKERS)
```

**How it works:**
```
Task 101: start_idx=0 → assign to WORKERS[0] = Worker1, rr_index becomes 1
Task 102: start_idx=1 → assign to WORKERS[1] = Worker2, rr_index becomes 0
Task 103: start_idx=0 → assign to WORKERS[0] = Worker1, rr_index becomes 1
...and so on
```

`% len(WORKERS)` ensures the index wraps around back to 0 after reaching the last worker.

---

#### Fault Tolerance

```python
for i in range(len(WORKERS)):
    worker = WORKERS[(start_idx + i) % len(WORKERS)]
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
5. If all workers fail → returns `status: "FAILED"`

**The `TimeoutTransport` class:**
```python
class TimeoutTransport(xmlrpc.client.Transport):
    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout   # sets 5s timeout on the TCP connection
        return conn
```
Without this, a dead worker would make the master wait forever. With it, after 5s of silence, an exception is raised and the next worker is tried.

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
Round-robin picks Worker1
      ↓
status = "RUNNING", worker = "Worker1"
      ↓
RPC call to Worker1
      ↓
Success?  → status = "COMPLETED", result = 120
Failure?  → Try Worker2
              Success? → status = "COMPLETED"
              Failure? → status = "FAILED"
```

---

### `client.py` — Client

**Role:** The user interface. Lets you submit tasks, check status, and view all tasks. Communicates with the master via XML-RPC.

```python
master = xmlrpc.client.ServerProxy(f"http://{MASTER_IP}:{MASTER_PORT}/", allow_none=True)
result = master.submit_task("factorial", [5])
```

This looks like a local function call, but it's actually:
1. Serializing `("factorial", [5])` to XML
2. Sending it over TCP to `MASTER_IP:9000`
3. Master receives it, processes it, sends back XML response
4. Client deserializes the response back into a Python dict

**Menu options:**
- **Option 1 (Submit task):** Takes task type and arguments from user, sends to master
- **Option 2 (Check task status):** Queries master for a specific task ID
- **Option 3 (View all tasks):** Gets entire task table from master and displays it
- **Option 4 (Exit):** Quits the client (master and workers keep running)

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
5. Round-robin distributes them: 10 → Worker1, 10 → Worker2
6. After all threads finish (`t.join()`), prints a summary with per-worker bar chart

**Why a new `ServerProxy` per thread?**
`ServerProxy` is not thread-safe — sharing one proxy between 20 threads causes race conditions. Each thread gets its own connection.

**Use for overload testing:**
Kill one worker before running the stress test. All 20 tasks will redirect to the surviving worker, demonstrating fault tolerance under load.

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
   Round-robin picks Worker1 (rr_index=0)
   Sets task_table[101]["status"] = "RUNNING"
   Calls: worker_proxy.execute_task(101, "factorial", [5])
   ↓ (XML-RPC over TCP to Worker1_IP:8001)

3. worker.py — execute_task()  (PC2 - Worker1 machine)
   Looks up TASK_HANDLERS["factorial"]
   Calls: factorial([5]) = math.factorial(5) = 120
   Returns: {taskID: 101, status: "COMPLETED", result: 120, workerID: "Worker1"}
   ↑ (XML-RPC response back to master over LAN)

4. master.py — back in submit_task()
   Updates task_table[101] = {status: "COMPLETED", worker: "Worker1", result: 120}
   Returns result dict to client
   ↑ (XML-RPC response back to client over LAN)

5. client.py
   Receives result dict
   Prints: Task ID: 101, Status: COMPLETED, Result: 120, Worker: Worker1
```

---

## Key Concepts Summary

| Concept | Where It Is | How It Works |
|---------|------------|--------------|
| RPC | All files | `xmlrpc.server` + `xmlrpc.client` handle network calls |
| Load Balancing | `master.py:rr_index` | Cycles through workers 0→1→0→1 |
| Fault Tolerance | `master.py:for loop` | Catches exceptions, tries next worker |
| Timeout | `master.py:TimeoutTransport` | TCP connection limit of 5 seconds |
| Task Monitoring | `master.py:task_table` | Dict tracking every task's lifecycle |
| Task States | `master.py` | PENDING → RUNNING → COMPLETED/FAILED |
| Threading | `master.py:ThreadedXMLRPCServer` | Each client request in its own thread |
| Multi-Machine Binding | `worker.py` + `master.py` | Bind to `0.0.0.0` — accept from any LAN machine |
| Network Config | `config.py:MASTER_IP + WORKERS` | LAN IPs for outbound connections |
| Timestamped Logging | `master.py:ts()` + `worker.py:ts()` | `[HH:MM:SS]` on every log — makes 5s fault detection gap measurable |
| Stress Testing | `stress_test.py` | 20 threads fire concurrent tasks, shows distribution |

---

## Why Each File Exists Separately

| File | Reason for Separation |
|------|----------------------|
| `config.py` | Change IPs/ports without touching logic — only file that differs per machine |
| `tasks.py` | Add new task types without touching network code |
| `worker.py` | Run multiple copies independently on different machines and ports |
| `master.py` | Single central coordinator — never run multiple copies |
| `client.py` | User-facing — can be run by multiple users on any machine simultaneously |
| `stress_test.py` | Standalone load tester — run from any machine, independent of client |

---

## What Would Break If You Changed Something

| Change | What Breaks |
|--------|------------|
| `MASTER_IP` in config.py ≠ master machine's actual IP | Client/stress_test can't connect to master |
| Worker `"host"` in config.py ≠ worker machine's actual IP | Master can't reach that worker, tasks FAIL |
| Worker bound to `"localhost"` instead of `"0.0.0.0"` | Only accepts connections from same machine — other machines can't connect |
| Master bound to `"localhost"` instead of `"0.0.0.0"` | Only clients on the same machine can connect |
| Task function raises unhandled exception | Worker returns FAILED (caught by try/except) |
| Both workers down | All tasks return FAILED after 10s total wait |
| Master down | Client throws ConnectionRefusedError immediately |
| `WORKER_TIMEOUT` too low (e.g., 0.1s) | Tasks fail even when workers are alive (connection too slow on LAN) |
| Firewall blocking ports 8001/8002/9000 | Remote machines can't connect even if IPs are correct |

---

## Real-World Equivalents

This project is a simplified version of how these real systems work:

| Real System | Our Equivalent |
|-------------|----------------|
| AWS Lambda / Google Cloud Functions | Worker nodes executing tasks |
| Kubernetes / Load Balancer | Master's round-robin logic |
| Circuit Breaker pattern | Fault tolerance + timeout |
| Task Queue (Celery, RabbitMQ) | task_table + PENDING/RUNNING states |
| gRPC (production-grade) | XML-RPC (our simpler version) |
