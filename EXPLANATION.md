# Project Explanation — RPC Distributed Task Execution System

---

## What This Project Does

This project simulates a **distributed computing system** where a central machine (master) receives tasks from a user (client) and distributes them to multiple worker machines for execution using **Remote Procedure Calls (RPC)**.

**In simple terms:**
> Instead of one machine doing all the work, the work is split across multiple machines. If one machine breaks down, another takes over. This is how real-world cloud systems like AWS, Google Cloud, and Hadoop work at a fundamental level.

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
+------------------+
|     CLIENT       |   ← You interact here (client.py)
|  submit_task()   |
+--------+---------+
         |
         | RPC call to master
         v
+------------------+
|     MASTER       |   ← Brain of the system (master.py)
|  Load Balancer   |   ← Decides which worker gets the task
|  Task Tracker    |   ← Keeps record of all tasks
|  Fault Detector  |   ← Detects unresponsive workers
+----+--------+----+
     |        |
     | RPC    | RPC
     v        v
+--------+ +--------+
|WORKER 1| |WORKER 2|   ← Do the actual computation (worker.py)
|port8001| |port8002|
+--------+ +--------+
```

---

## File-by-File Explanation

---

### `config.py` — Configuration

```python
WORKERS = [
    {"id": "Worker1", "host": "localhost", "port": 8001},
    {"id": "Worker2", "host": "localhost", "port": 8002},
]
MASTER_HOST = "localhost"
MASTER_PORT = 9000
WORKER_TIMEOUT = 5
```

**What it does:**
- Central place to define where workers and master are running
- `WORKER_TIMEOUT = 5` means: if a worker doesn't reply in 5 seconds, it's considered failed
- To add a 3rd worker, you'd add `{"id": "Worker3", "host": "localhost", "port": 8003}` here
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
server = SimpleXMLRPCServer(("localhost", port), ...)
server.register_function(execute_task, "execute_task")
server.serve_forever()
```
- Opens a TCP port
- Registers `execute_task` as the callable RPC method
- Loops forever waiting for calls

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
master = xmlrpc.client.ServerProxy("http://localhost:9000/", allow_none=True)
result = master.submit_task("factorial", [5])
```

This looks like a local function call, but it's actually:
1. Serializing `("factorial", [5])` to XML
2. Sending it over TCP to `localhost:9000`
3. Master receives it, processes it, sends back XML response
4. Client deserializes the response back into a Python dict

**Menu options:**
- **Option 1 (Submit task):** Takes task type and arguments from user, sends to master
- **Option 2 (Check task status):** Queries master for a specific task ID
- **Option 3 (View all tasks):** Gets entire task table from master and displays it
- **Option 4 (Exit):** Quits the client (master and workers keep running)

---

## Data Flow — End to End

Here's what happens when you type `factorial(5)`:

```
1. client.py
   User picks "1. Submit task", type=factorial, number=5
   Calls: master_proxy.submit_task("factorial", [5])
   ↓ (XML-RPC over TCP to port 9000)

2. master.py — submit_task()
   Assigns task_id = 101
   Sets task_table[101] = {status: "PENDING", worker: None, result: None}
   Round-robin picks Worker1 (rr_index=0)
   Sets task_table[101]["status"] = "RUNNING"
   Calls: worker_proxy.execute_task(101, "factorial", [5])
   ↓ (XML-RPC over TCP to port 8001)

3. worker.py — execute_task()
   Looks up TASK_HANDLERS["factorial"]
   Calls: factorial([5]) = math.factorial(5) = 120
   Returns: {taskID: 101, status: "COMPLETED", result: 120, workerID: "Worker1"}
   ↑ (XML-RPC response back to master)

4. master.py — back in submit_task()
   Updates task_table[101] = {status: "COMPLETED", worker: "Worker1", result: 120}
   Returns result dict to client
   ↑ (XML-RPC response back to client)

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

---

## Why Each File Exists Separately

| File | Reason for Separation |
|------|----------------------|
| `config.py` | Change ports/hosts without touching logic |
| `tasks.py` | Add new task types without touching network code |
| `worker.py` | Run multiple copies independently on different ports |
| `master.py` | Single central coordinator — never run multiple copies |
| `client.py` | User-facing — can be run by multiple users simultaneously |

---

## What Would Break If You Changed Something

| Change | What Breaks |
|--------|------------|
| Master port in config.py ≠ client connect port | Client can't connect to master |
| Worker port in config.py ≠ actual `python worker.py` port | Master can't reach that worker |
| Task function raises unhandled exception | Worker returns FAILED (caught by try/except) |
| Both workers down | All tasks return FAILED after 10s total wait |
| Master down | Client throws ConnectionRefusedError immediately |
| WORKER_TIMEOUT too low (e.g., 0.1s) | Tasks fail even when workers are running (too fast timeout) |

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
