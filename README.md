# RPC-Based Distributed Task Execution System

A distributed computing case study built with Python and XML-RPC. Clients submit tasks to a master node, which distributes them across worker nodes using round-robin load balancing with automatic fault tolerance.

---

## Architecture

```
                        ┌─────────────┐
          ┌────────────▶│   Worker 1  │ :8001
          │  Round-Robin│  (PC / VM)  │
┌──────┐  │             └─────────────┘
│Client│──▶  Master
│      │  │   :9000     ┌─────────────┐
└──────┘  └────────────▶│   Worker 2  │ :8002
                        │  (PC / VM)  │
                        └─────────────┘
```

- **Client** — interactive CLI to submit tasks and monitor status
- **Master** — threaded XML-RPC server, routes tasks, tracks status, handles worker failures
- **Workers** — XML-RPC servers that execute the actual task functions

All three can run on the same machine (localhost) or on separate machines over a LAN.

---

## Features

- **Round-robin load balancing** — tasks are distributed evenly across available workers
- **Fault tolerance** — if a worker is unreachable, the master retries on the next worker (5s timeout per attempt)
- **Concurrent client support** — master uses `ThreadingMixIn` to handle multiple clients at once
- **Real-time task monitoring** — every task has an ID and lifecycle: `PENDING → RUNNING → COMPLETED / FAILED`
- **Multi-machine LAN support** — bind address is `0.0.0.0`; configure IPs in `config.py`
- **Timestamped logs** — all master and worker output is prefixed with `[HH:MM:SS]` for fault detection visibility
- **Stress testing** — included script fires 20 concurrent tasks and prints a per-worker summary

---

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Language   | Python 3 (stdlib only)            |
| RPC        | `xmlrpc.server`, `xmlrpc.client`  |
| Concurrency| `threading`, `ThreadingMixIn`     |
| Transport  | HTTP / TCP with custom timeout    |

No external dependencies — runs out of the box with any Python 3 installation.

---

## File Structure

```
RPC_communication/
├── config.py          # IPs, ports, timeout settings
├── tasks.py           # Task function definitions
├── worker.py          # Worker XML-RPC server
├── master.py          # Master XML-RPC server (load balancer)
├── client.py          # Interactive CLI client
├── stress_test.py     # 20-thread concurrent load test
├── TESTING_GUIDE.md   # Step-by-step test cases with expected outputs
├── EXPLANATION.md     # Detailed architecture and code explanation
└── PRESENTATION.md    # PPT structure and viva Q&A
```

---

## Quick Start (Single Machine)

Open **4 separate terminals** in the project folder:

```bash
# Terminal 1 — start worker on port 8001
python worker.py 8001

# Terminal 2 — start worker on port 8002
python worker.py 8002

# Terminal 3 — start master
python master.py

# Terminal 4 — run the interactive client
python client.py
```

---

## Multi-Machine Setup (LAN)

**1. Edit `config.py`** on every machine:

```python
MASTER_IP   = "192.168.x.x"   # LAN IP of the machine running master.py

WORKERS = [
    {"id": "Worker1", "host": "192.168.x.y", "port": 8001},  # Worker 1 machine IP
    {"id": "Worker2", "host": "192.168.x.z", "port": 8002},  # Worker 2 machine IP
]
```

> Find your IP: `ipconfig` on Windows, `ifconfig` on Mac/Linux.

**2. Open firewall ports** on each machine:
- Worker machines: allow inbound TCP on `8001` / `8002`
- Master machine: allow inbound TCP on `9000`

**3. Run as in Quick Start** — each process on its respective machine.

---

## Supported Tasks

| Task        | Input            | Example                    |
|-------------|------------------|----------------------------|
| `add`       | Two integers     | `add([10, 5])` → `15`      |
| `factorial` | One integer      | `factorial([6])` → `720`   |
| `reverse`   | One string       | `reverse(["hello"])` → `"olleh"` |

---

## API Reference

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

---

## Stress Test

```bash
python stress_test.py
```

Fires 20 concurrent tasks (mix of add, factorial, reverse) and prints a per-worker distribution chart:

```
Worker1  ██████████  10
Worker2  ██████████  10
Total time: 1.83s
```

---

## Known Limitations

| Limitation                  | Notes                                              |
|-----------------------------|----------------------------------------------------|
| No heartbeat / health check | Failures only detected when a task times out (5s)  |
| Synchronous task execution  | Master blocks per task; no async pipeline          |
| No persistent storage       | Task table is in-memory; lost on master restart     |
| No authentication           | Any client on the network can connect              |

---

## Documentation

- [`TESTING_GUIDE.md`](TESTING_GUIDE.md) — 8 test cases with exact inputs and expected outputs
- [`EXPLANATION.md`](EXPLANATION.md) — full architecture walkthrough, file-by-file explanation, data flow
- [`PRESENTATION.md`](PRESENTATION.md) — 10-slide PPT outline and viva Q&A preparation
