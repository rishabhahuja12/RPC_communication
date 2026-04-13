# RPC-Based Distributed Task Execution System

A distributed computing system built with Python and XML-RPC. Clients submit tasks to a master node, which discovers workers dynamically through a **service discovery registry** and distributes tasks using round-robin load balancing with automatic fault tolerance and **auto-scaling**.

---

## Architecture

```
                                    ┌──────────────┐
                                    │   REGISTRY   │ :7000
                                    │ (Service     │
                               ┌───▶│  Discovery)  │◀── heartbeat ──┐
                               │    └──────────────┘                │
                               │         ▲                          │
                          get_workers()  │ register/                │
                               │         │ deregister               │
┌──────┐       ┌────────────┐  │    ┌────┴────────┐          ┌─────┴───────┐
│Client│──────▶│   Master   │──┘    │  Worker 1   │          │  Worker 2   │
│      │       │   :9000    │──────▶│  :8001      │          │  :8002      │
└──────┘       │ AutoScaler │──────▶│             │          │             │
               └────────────┘       └─────────────┘          └─────────────┘
                     │                                             ▲
                     └── RPC task execution ───────────────────────┘
```

- **Registry** — service discovery server; workers register here, master queries here
- **Client** — interactive CLI to submit tasks and monitor cluster status
- **Master** — threaded XML-RPC server, discovers workers at runtime, auto-scales, tracks status, handles failures
- **Workers** — XML-RPC servers that self-register and execute tasks

All components can run on the same machine (localhost) or on separate machines over a LAN.

---

## Features

- **Service discovery** — workers self-register with the registry on startup; no hardcoded IPs
- **Heartbeat health checks** — workers send heartbeats every 3s; registry reaps stale workers after 10s
- **Auto-scaling** — master spawns/kills worker processes based on demand (configurable min/max)
- **Round-robin load balancing** — tasks distributed evenly across discovered workers
- **Fault tolerance** — 5s TCP timeout per worker; automatic retry on next worker; "Service Unavailable" when all down
- **Concurrent client support** — master uses `ThreadingMixIn` for multi-client handling
- **Real-time monitoring** — task lifecycle tracking + live cluster status view
- **Dynamic worker join/leave** — start a new worker anytime, it auto-registers and receives tasks
- **Multi-machine LAN support** — bind address is `0.0.0.0`; configure IPs in `config.py`
- **Timestamped logs** — all output prefixed with `[HH:MM:SS]` for fault detection visibility
- **Stress testing** — fires 20 concurrent tasks with per-worker distribution summary

---

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Language   | Python 3 (stdlib only)            |
| RPC        | `xmlrpc.server`, `xmlrpc.client`  |
| Concurrency| `threading`, `ThreadingMixIn`     |
| Transport  | HTTP / TCP with custom timeout    |
| Scaling    | `subprocess` (auto-spawning)      |

No external dependencies — runs out of the box with any Python 3 installation.

---

## File Structure

```
RPC_communication/
├── config.py          # IPs, ports, timeouts, auto-scaling settings
├── tasks.py           # Task function definitions
├── registry.py        # Service discovery server (NEW)
├── worker.py          # Worker XML-RPC server (self-registers)
├── master.py          # Master XML-RPC server (dynamic discovery + auto-scaler)
├── client.py          # Interactive CLI client
├── stress_test.py     # 20-thread concurrent load test
├── TESTING_GUIDE.md   # Step-by-step test cases with expected outputs
├── EXPLANATION.md     # Detailed architecture and code explanation
└── PRESENTATION.md    # PPT structure and viva Q&A
```

---

## Quick Start (Single Machine)

Open **5 separate terminals** in the project folder:

```bash
# Terminal 1 — start the service discovery registry
python registry.py

# Terminal 2 — start worker on port 8001 (auto-registers with registry)
python worker.py 8001

# Terminal 3 — start worker on port 8002 (auto-registers with registry)
python worker.py 8002

# Terminal 4 — start master (discovers workers from registry, auto-scaler starts)
python master.py

# Terminal 5 — run the interactive client
python client.py
```

> **Note:** Workers can be started in any order, before or after the master. They register themselves with the registry automatically.

---

## Multi-Machine Setup (LAN)

**1. Edit `config.py`** on every machine:

```python
MASTER_IP   = "192.168.x.x"    # LAN IP of the machine running master.py
REGISTRY_IP = "192.168.x.x"    # LAN IP of the machine running registry.py
```

> Find your IP: `ipconfig` on Windows, `ifconfig` on Mac/Linux.

**2. Open firewall ports** on each machine:
- Registry machine: allow inbound TCP on `7000`
- Worker machines: allow inbound TCP on the worker's port (e.g., `8001`)
- Master machine: allow inbound TCP on `9000`

**3. Start each component on its machine:**

```bash
# Registry machine:
python registry.py

# Worker machines (use --host to tell registry your LAN IP):
python worker.py 8001 --host 192.168.x.y
python worker.py 8002 --host 192.168.x.z

# Master machine:
python master.py

# Client (any machine):
python client.py
```

No need to list worker IPs anywhere — they self-register!

---

## Supported Tasks

| Task        | Input            | Example                    |
|-------------|------------------|----------------------------|
| `add`       | Two integers     | `add([10, 5])` → `15`      |
| `factorial` | One integer      | `factorial([6])` → `720`   |
| `reverse`   | One string       | `reverse(["hello"])` → `"olleh"` |

---

## API Reference

**Registry RPC** (called by workers and master):
```
register_worker(worker_id, host, port) → True
deregister_worker(worker_id)           → True/False
heartbeat(worker_id)                   → True/False
get_workers()                          → [ {id, host, port}, ... ]
get_worker_count()                     → int
```

**Worker RPC** (called by master only):
```
execute_task(task_id, task_type, task_data)
→ { taskID, status, result, workerID }
```

**Master RPC** (called by client / stress_test):
```
submit_task(task_type, task_data)
→ { taskID, status, result, workerID }

get_task_status(task_id)
→ { taskID, status, worker, result }

get_all_tasks()
→ [ { taskID, status, worker, result }, ... ]

get_cluster_status()
→ { worker_count, workers, pending_tasks, running_tasks, completed_tasks,
    failed_tasks, auto_scale, auto_scale_range, spawned_workers }
```

---

## Service Discovery

Workers register with the registry on startup and send heartbeats every 3 seconds. If a worker misses heartbeats for 10 seconds (e.g., crash or network failure), the registry automatically removes it. The master queries the registry before every task assignment to get the current live worker list.

```
Worker starts → register_worker("Worker1", "localhost", 8001)
Every 3s      → heartbeat("Worker1")
Worker stops  → deregister_worker("Worker1")   (graceful)
                or reaper removes after 10s     (crash)
```

---

## Auto-Scaling

When enabled (`AUTO_SCALE = True` in `config.py`), the master runs a background thread that:

- **Scales up:** Spawns new worker processes when `pending_tasks / worker_count > SCALE_UP_THRESHOLD`
- **Scales down:** Terminates idle auto-spawned workers after `SCALE_DOWN_IDLE` seconds
- **Maintains bounds:** Never drops below `MIN_WORKERS` or exceeds `MAX_WORKERS`

```
Config defaults:
  MIN_WORKERS        = 2
  MAX_WORKERS        = 6
  SCALE_UP_THRESHOLD = 2 tasks per worker
  SCALE_DOWN_IDLE    = 30 seconds
  WORKER_PORT_RANGE  = 8001–8020
```

---

## Fault Tolerance Demo

Stop a worker mid-session (`Ctrl+C` in its terminal), then submit a task via the client.

Expected master output:
```
[14:02:10] [Master] Task 101 submitted: factorial([10])
[14:02:10] [Master] Assigning task 101 to Worker1
[14:02:15] [Master] Worker1 unreachable (timed out). Trying next worker...
[14:02:15] [Master] Assigning task 101 to Worker2
[14:02:15] [Master] Task 101 → COMPLETED | Result: 3628800
```

The **5-second gap** between lines 2 and 3 is the fault detection latency — the TCP timeout expiring before failover kicks in.

If **all workers** are down:
```
  Task ID : 101
  Status  : FAILED
  Result  : Service Unavailable
  Worker  : None
```

---

## Stress Test

```bash
python stress_test.py
```

Fires 20 concurrent tasks and prints a per-worker distribution chart:

```
Worker1  ██████████  10
Worker2  ██████████  10
Unique workers: 2
Total time: 1.83s
```

---

## Known Limitations

| Limitation                  | Notes                                              |
|-----------------------------|-------------------------------------------------------|
| Synchronous task execution  | Master blocks per task; no async pipeline              |
| No persistent storage       | Task table is in-memory; lost on master restart        |
| No authentication           | Any client on the network can connect                  |
| Local auto-scaling only     | Auto-scaler spawns workers on master's machine only    |
| Registry is SPOF            | If registry crashes, new discovery stops (existing connections keep working) |

---

## Documentation

- [`TESTING_GUIDE.md`](TESTING_GUIDE.md) — 13 test cases with exact inputs and expected outputs
- [`EXPLANATION.md`](EXPLANATION.md) — full architecture walkthrough, file-by-file explanation, data flow
- [`PRESENTATION.md`](PRESENTATION.md) — 10-slide PPT outline and viva Q&A preparation
