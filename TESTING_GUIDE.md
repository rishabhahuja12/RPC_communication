# Testing Guide — RPC Distributed Task Execution System

## Setup

### Option A — Single Machine (Local Testing)

Keep `config.py` as-is (all `localhost`). Open 5 terminals:

```
Terminal 1:  python registry.py        ← START THIS FIRST
Terminal 2:  python worker.py 8001
Terminal 3:  python worker.py 8002
Terminal 4:  python master.py
Terminal 5:  python client.py
```

### Option B — Multi-Machine (Real Distributed, Same WiFi)

1. Edit `config.py` on **all machines** with actual LAN IPs:
   ```python
   MASTER_IP   = "192.168.x.x"    # IP of PC running master.py
   REGISTRY_IP = "192.168.x.x"    # IP of PC running registry.py
   ```
2. Each machine clones the repo and edits `config.py` with the same IPs
3. Allow firewall ports: 7000 (registry), 9000 (master), 8001+ (workers)
    Windows Defender Firewall → Advanced Settings
    → Inbound Rules → New Rule → Port → TCP → 7000 → Allow

    For Mac
      sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add python3
      # or just turn off Mac Firewall temporarily for demo:
      System Preferences → Security & Privacy → Firewall → Turn Off

Then run on each machine:
```
# Registry machine:
python registry.py

# Friend 1's machine (Worker):
python worker.py 8001 --host 192.168.x.y

# Friend 2's machine (Worker):
python3 worker.py 8002 --host 192.168.x.z

# Your machine:
python master.py

# Client — run from any machine:
python client.py
```

---

Wait until you see:
- `[HH:MM:SS] [Registry] Service Discovery running on 0.0.0.0:7000`
- `[HH:MM:SS] [Worker1] Registered with registry at localhost:7000`
- `[HH:MM:SS] [Worker2] Registered with registry at localhost:7000`
- `[HH:MM:SS] [Master] Running on 0.0.0.0:9000 (clients connect via localhost:9000)`

> All log lines include a timestamp `[HH:MM:SS]`. This makes the **5-second fault detection gap visually obvious** during the demo.

Then run the client and follow the test cases below.

---

## Test 1 — Single Task Execution (Factorial)

**Goal:** Verify a single task runs end-to-end correctly with dynamic worker discovery.

### Steps in client (Terminal 5):

```
Choice: 1
Task type: factorial
Number: 5
```

### Expected Output in Client:
```
Submitting: factorial([5]) ...

  Task ID : 101
  Status  : COMPLETED
  Result  : 120
  Worker  : Worker1
```

### Expected Output in Master (Terminal 4):
```
[10:32:41] [Master] Task 101 submitted: factorial([5])
[10:32:41] [Master] Assigning task 101 to Worker1
[10:32:41] [Master] Task 101 → COMPLETED | Result: 120
```

### Expected Output in Worker1 (Terminal 2):
```
[10:32:41] [Worker1] Task 101 received: factorial([5])
[10:32:41] [Worker1] Task 101 completed. Result: 120
```

---

## Test 2 — Round Robin Load Balancing (Multiple Tasks)

**Goal:** Verify tasks alternate between Worker1 and Worker2.

### Submit 4 tasks one after another in the client:

**Task 1:**
```
Choice: 1
Task type: factorial
Number: 5
```
Expected: Task 101, Worker1, Result: 120

**Task 2:**
```
Choice: 1
Task type: add
First number : 10
Second number: 20
```
Expected: Task 102, Worker2, Result: 30

**Task 3:**
```
Choice: 1
Task type: reverse
String: hello
```
Expected: Task 103, Worker1, Result: olleh

**Task 4:**
```
Choice: 1
Task type: factorial
Number: 6
```
Expected: Task 104, Worker2, Result: 720

### Summary of Round Robin Pattern:
```
Task 101 → Worker1
Task 102 → Worker2
Task 103 → Worker1
Task 104 → Worker2
```

---

## Test 3 — Task Status Tracking

**Goal:** Verify the task table records status correctly.

After running Test 2, do the following:

### Check individual task status:
```
Choice: 2
Task ID: 101
```

Expected:
```
  Task 101:
    Status : COMPLETED
    Worker : Worker1
    Result : 120
```

### View all tasks:
```
Choice: 3
```

Expected:
```
ID       Status       Worker       Result
--------------------------------------------------
101      COMPLETED    Worker1      120
102      COMPLETED    Worker2      30
103      COMPLETED    Worker1      olleh
104      COMPLETED    Worker2      720
```

---

## Test 4 — Worker Failure + Fault Tolerance

**Goal:** Verify master detects worker failure and reassigns the task.

### Steps:

1. **Kill Worker1** — go to Terminal 2, press `Ctrl+C`
   - You will see: `[Worker1] Shutting down...` → `Deregistered from registry` → `Done.`

2. **In the client, submit a new task:**
```
Choice: 1
Task type: add
First number : 100
Second number: 200
```

3. **Wait ~5 seconds** (if the round-robin tries to reach Worker1 before the registry deregisters it)

### Expected Output in Client:
```
Submitting: add([100, 200]) ...

  Task ID : 105
  Status  : COMPLETED
  Result  : 300
  Worker  : Worker2
```

### Expected Output in Master (Terminal 4):
```
[10:35:10] [Master] Task 105 submitted: add([100, 200])
[10:35:10] [Master] Assigning task 105 to Worker2
[10:35:10] [Master] Task 105 → COMPLETED | Result: 300
```

> **Note:** With graceful shutdown (Ctrl+C), the worker deregisters from the registry, so the master discovers only Worker2 on its next `get_workers()` call. No 5-second gap in this case!

> **Alternative:** If the worker is killed forcefully (e.g., `taskkill`), the master may still attempt to reach it, triggering the 5-second timeout before failover.

---

## Test 5 — All Workers Down (Service Unavailable)

**Goal:** Verify the system returns "Service Unavailable" when no workers are available.

### Steps:

1. Kill Worker1 (Ctrl+C Terminal 2) if not already done
2. Kill Worker2 (Ctrl+C Terminal 3)
3. Wait 10 seconds for the registry to reap any stale entries
4. Submit a task:

```
Choice: 1
Task type: factorial
Number: 4
```

### Expected Output in Client:
```
  Task ID : 106
  Status  : FAILED
  Result  : Service Unavailable
  Worker  : None
```

### Expected Output in Master:
```
[10:40:01] [Master] Task 106 submitted: factorial([4])
[10:40:01] [Master] Task 106 FAILED — Service Unavailable (no workers registered)
```

---

## Test 6 — Worker Recovery After Restart

**Goal:** Verify workers can restart, re-register, and resume handling tasks.

### Steps:

1. Restart Worker1:
```
Terminal 2:  python worker.py 8001
```

2. Wait for the registration log:
```
[10:41:05] [Worker1] Registered with registry at localhost:7000
```

3. Submit a task in the client:
```
Choice: 1
Task type: reverse
String: world
```

### Expected:
```
  Task ID : 107
  Status  : COMPLETED
  Result  : dlrow
  Worker  : Worker1
```

The system recovers automatically — no restart of master or client needed.

---

## Test 7 — Invalid Task Type

**Goal:** Verify graceful handling of unsupported task types.

```
Choice: 1
Task type: multiply
```

### Expected in Client:
```
Unknown task type. Choose: add | factorial | reverse
```

The client validates input before even calling the master.

---

## Test 8 — Stress Test (Concurrent Overload)

**Goal:** Fire 20 tasks simultaneously and verify round-robin distribution and system stability under load.

### Steps:

1. Make sure both workers and master are running
2. Run from any machine (including a 3rd machine on the same network):

```bash
python stress_test.py
```

### Expected Output:
```
======================================================================
  STRESS TEST — Firing 20 tasks simultaneously
  Target master: localhost:9000
======================================================================
  Task  101 | factorial  | COMPLETED | Worker: Worker1   | Result: 1
  Task  102 | add        | COMPLETED | Worker: Worker2   | Result: 15
  Task  103 | reverse    | COMPLETED | Worker: Worker1   | Result: 0sserts
  ...

======================================================================
  RESULTS SUMMARY
======================================================================
  Total tasks    : 20
  Completed      : 20
  Failed         : 0
  Time taken     : 2.41 seconds
  Unique workers : 2

  Tasks per worker:
    Worker1      ██████████  (10 tasks)
    Worker2      ██████████  (10 tasks)
======================================================================
```

---

## Test 9 — Dynamic Worker Join (Service Discovery)

**Goal:** Start a 3rd worker mid-session and verify it immediately receives tasks.

### Steps:

1. With registry, master, Worker1, and Worker2 running, open a new terminal:
```
Terminal 6:  python worker.py 8003
```

2. Check registry log (Terminal 1):
```
[10:45:10] [Registry] ✔ Registered Worker3 at localhost:8003
```

3. Submit 3 tasks in the client:

### Expected Round Robin (3 workers):
```
Task → Worker1
Task → Worker2
Task → Worker3
```

4. Verify with cluster status:
```
Choice: 4
```

Expected:
```
  ── Cluster Status ──
  Active workers : 3
    • Worker1@localhost:8001
    • Worker2@localhost:8002
    • Worker3@localhost:8003
  ...
```

**Key point:** Worker3 was added without restarting the master, editing config.py, or doing anything except running `python worker.py 8003`.

---

## Test 10 — Heartbeat-Based Removal (Crash Detection)

**Goal:** Kill a worker forcefully (not Ctrl+C) and verify the registry reaps it after the heartbeat timeout.

### Steps:

1. Find Worker1's terminal and **close the terminal window entirely** (or use `taskkill /F /PID <pid>` on Windows)
   - This prevents the clean deregister
2. Watch the **Registry log** (Terminal 1)

### Expected in Registry (after ~10 seconds):
```
[10:48:20] [Registry] ⚠ Reaped Worker1 at localhost:8001 (no heartbeat for 10s)
```

3. Submit a task — it should go to Worker2 (Worker1 is no longer in the pool)

4. Check cluster status:
```
Choice: 4
```
Expected: Only Worker2 (and Worker3 if still running) listed.

---

## Test 11 — Auto-Scaling Up

**Goal:** Observe the auto-scaler spawn new workers when demand exceeds capacity.

### Steps:

1. Stop all workers (kill all worker terminals)
2. Make sure `AUTO_SCALE = True` in `config.py`
3. Start only the registry and master:
```
Terminal 1:  python registry.py
Terminal 2:  python master.py
```

4. The auto-scaler should detect 0 workers < MIN_WORKERS (2) and spawn workers:
```
[10:50:05] [AutoScaler] ⬆ Scaling UP — spawning Worker1 on port 8001
[10:50:05] [AutoScaler] ⬆ Worker1 spawned (PID: 12345)
[10:50:10] [AutoScaler] ⬆ Scaling UP — spawning Worker2 on port 8002
[10:50:10] [AutoScaler] ⬆ Worker2 spawned (PID: 12346)
```

5. Run `stress_test.py` — all tasks should complete across auto-spawned workers

6. Check cluster status (Option 4) — should show:
```
  Auto-spawned   : Worker1, Worker2
```

---

## Test 12 — Auto-Scaling Down

**Goal:** Verify idle auto-spawned workers are terminated after SCALE_DOWN_IDLE seconds.

### Steps:

1. After Test 11, wait 30+ seconds without submitting any tasks
2. Watch master log for scale-down events:
```
[10:51:45] [AutoScaler] ⬇ Scaling DOWN — terminating Worker3 (PID: 12347)
[10:51:45] [AutoScaler] ⬇ Worker3 terminated
```

3. Auto-scaler will NOT go below MIN_WORKERS (2). So Worker1 and Worker2 should remain.

4. Check cluster status to verify the surviving workers.

---

## Test 13 — Cluster Status View

**Goal:** Verify Option 4 in the client shows accurate live cluster state.

### Steps:

```
Choice: 4
```

### Expected:
```
  ── Cluster Status ──
  Active workers : 2
    • Worker1@localhost:8001
    • Worker2@localhost:8002
  Pending tasks  : 0
  Running tasks  : 0
  Completed      : 20
  Failed         : 1
  Auto-scaling   : ON (2-6)
  Auto-spawned   : Worker1, Worker2
```

---

## Quick Reference: All Test Cases

| Test | What It Tests | Expected Outcome |
|------|--------------|--------------------|
| 1 | Single factorial task | Result: 120, Worker1 |
| 2 | 4 tasks round-robin | Alternates Worker1/Worker2 |
| 3 | Task status tracking | Correct status in table |
| 4 | Worker1 killed (Ctrl+C) | Worker deregisters; task goes to Worker2 |
| 5 | Both workers killed | Status: FAILED, Result: Service Unavailable |
| 6 | Worker restarted | Re-registers; system resumes normally |
| 7 | Invalid task type | Client rejects, no crash |
| 8 | 20 concurrent tasks | Even split, all complete, bar chart shown |
| 9 | 3rd worker joins mid-session | Auto-discovered, receives tasks immediately |
| 10 | Worker killed forcefully | Registry reaps after 10s heartbeat timeout |
| 11 | Auto-scaling up | Master spawns workers when demand exceeds capacity |
| 12 | Auto-scaling down | Idle auto-spawned workers terminated after 30s |
| 13 | Cluster status view | Active workers, tasks, auto-scaler state shown |

---

## Task IDs Reference

Task IDs start at 101 and increment by 1 per submission.
- 1st task = ID 101
- 2nd task = ID 102
- etc.
