# Testing Guide — RPC Distributed Task Execution System

## Setup

### Option A — Single Machine (Local Testing, Auto-Scale ON)

Keep `config.py` as-is (all `localhost`, `AUTO_SCALE = True`). Open **3 terminals**:

```
Terminal 1:  python registry.py        ← START THIS FIRST
Terminal 2:  python master.py          ← auto-spawns MIN_WORKERS (2) workers
Terminal 3:  python client.py          ← submit tasks here
```

> The auto-scaler spawns workers automatically. You don't need to start them manually.

For admin monitoring, open a 4th terminal:
```
Terminal 4:  python admin.py           ← full system visibility
```

### Option A2 — Single Machine (Manual Workers, Auto-Scale OFF)

Set `AUTO_SCALE = False` in `config.py`. Open **5 terminals**:

```
Terminal 1:  python registry.py        ← START THIS FIRST
Terminal 2:  python worker.py 8001
Terminal 3:  python worker.py 8002
Terminal 4:  python master.py
Terminal 5:  python client.py
```

For admin monitoring, open a 6th terminal:
```
Terminal 6:  python admin.py
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

# Admin — run on master machine only:
python admin.py
```

> See [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) for detailed Windows ↔ Mac multi-device setup instructions.

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

### Steps in client (Terminal 3):

```
Choice: 1
Operation: factorial
Number: 5
```

### Expected Output in Client:
```
Processing factorial([5]) ...

  factorial(5) = 120
```

> Note: The client sees only the computation result — no task ID, no worker name.

### Expected Output in Master (Terminal 2):
```
[10:32:41] [Master] Task 101 submitted by Client_a3f8c2e1: factorial([5])
[10:32:41] [Master] Assigning task 101 to Worker1
[10:32:41] [Master] Task 101 → COMPLETED | Result: 120
```

### Expected Output in Worker1:
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
Operation: factorial
Number: 5
```
Expected client output: `factorial(5) = 120`

**Task 2:**
```
Choice: 1
Operation: add
First number : 10
Second number: 20
```
Expected client output: `10 + 20 = 30`

**Task 3:**
```
Choice: 1
Operation: reverse
String: hello
```
Expected client output: `reverse("hello") = "olleh"`

**Task 4:**
```
Choice: 1
Operation: factorial
Number: 6
```
Expected client output: `factorial(6) = 720`

### Verify via Admin (Terminal 4):
```
Choice: 1   (View all tasks)
```

Expected admin output:
```
  ID       Type         Status       Worker       Client             Result
  --------------------------------------------------------------------------------
  101      factorial    COMPLETED    Worker1      Client_a3f8c2e1    120
  102      add          COMPLETED    Worker2      Client_a3f8c2e1    30
  103      reverse      COMPLETED    Worker1      Client_a3f8c2e1    olleh
  104      factorial    COMPLETED    Worker2      Client_a3f8c2e1    720
```

Round-robin pattern: Worker1 → Worker2 → Worker1 → Worker2

---

## Test 3 — Client Isolation (Two Clients)

**Goal:** Verify that one client cannot see another client's tasks.

### Steps:

1. **Open a second client** in a new terminal:
```
Terminal 5:  python client.py
```
> This client gets a different `client_id` (e.g., `Client_b7d9e4f2`)

2. **Submit a task from the second client:**
```
Choice: 1
Operation: add
First number : 100
Second number: 200
```
Expected: `100 + 200 = 300`

3. **View past results from the second client:**
```
Choice: 2
```
Expected — **only sees its own task:**
```
  Your Past Results:
  -------------------------------------------------------
    1. 100 + 200 = 300
  -------------------------------------------------------
```

4. **Switch to the first client** (Terminal 3) and view past results:
```
Choice: 2
```
Expected — **only sees its own 4 tasks:**
```
  Your Past Results:
  -------------------------------------------------------
    1. factorial(5) = 120
    2. 10 + 20 = 30
    3. reverse("hello") = "olleh"
    4. factorial(6) = 720
  -------------------------------------------------------
```

5. **Verify via Admin** (Terminal 4):
```
Choice: 4   (View client summary)
```
Expected:
```
  Client ID              Total    Done     Failed   Pending  Running
  --------------------------------------------------------------
  Client_a3f8c2e1        4        4        0        0        0
  Client_b7d9e4f2        1        1        0        0        0

  Total clients: 2
```

The admin sees all clients, but each client only sees their own data.

---

## Test 4 — Worker Failure + Fault Tolerance

**Goal:** Verify master detects worker failure and reassigns the task.

### Steps:

1. **Kill Worker1** — go to the Worker1 terminal, press `Ctrl+C`
   - You will see: `[Worker1] Shutting down...` → `Deregistered from registry` → `Done.`

2. **In the client, submit a new task:**
```
Choice: 1
Operation: add
First number : 100
Second number: 200
```

3. **Wait ~5 seconds** (if the round-robin tries to reach Worker1 before the registry deregisters it)

### Expected Output in Client:
```
Processing add([100, 200]) ...

  100 + 200 = 300
```
> The client has no idea Worker1 failed — it just gets the result.

### Expected Output in Master:
```
[10:35:10] [Master] Task 105 submitted by Client_a3f8c2e1: add([100, 200])
[10:35:10] [Master] Assigning task 105 to Worker2
[10:35:10] [Master] Task 105 → COMPLETED | Result: 300
```

> **Note:** With graceful shutdown (Ctrl+C), the worker deregisters from the registry, so the master discovers only Worker2 on its next `get_workers()` call. No 5-second gap in this case!

> **Alternative:** If the worker is killed forcefully (e.g., `taskkill`), the master may still attempt to reach it, triggering the 5-second timeout before failover.

---

## Test 5 — All Workers Down (Service Unavailable)

**Goal:** Verify the system returns a failure message when no workers are available.

### Steps:

1. Kill Worker1 (Ctrl+C) if not already done
2. Kill Worker2 (Ctrl+C)
3. Wait 10 seconds for the registry to reap any stale entries
4. Submit a task in the client:

```
Choice: 1
Operation: factorial
Number: 4
```

### Expected Output in Client:
```
Processing factorial([4]) ...

  Computation failed. Please try again later.
```
> No task IDs, no worker IDs, no internal details — just a clean failure message.

### Expected Output in Master:
```
[10:40:01] [Master] Task 106 submitted by Client_a3f8c2e1: factorial([4])
[10:40:01] [Master] Task 106 FAILED — Service Unavailable (no workers registered)
```

### Verify via Admin:
```
Choice: 2
Task ID: 106
```
Expected:
```
  Task 106:
    Type      : factorial
    Input     : [4]
    Status    : FAILED
    Worker    : None
    Client    : Client_a3f8c2e1
    Result    : Service Unavailable
```

---

## Test 6 — Worker Recovery After Restart

**Goal:** Verify workers can restart, re-register, and resume handling tasks.

### Steps:

1. Restart Worker1:
```
python worker.py 8001
```

2. Wait for the registration log:
```
[10:41:05] [Worker1] Registered with registry at localhost:7000
```

3. Submit a task in the client:
```
Choice: 1
Operation: reverse
String: world
```

### Expected client output:
```
  reverse("world") = "dlrow"
```

The system recovers automatically — no restart of master or client needed.

---

## Test 7 — Invalid Task Type

**Goal:** Verify graceful handling of unsupported task types.

```
Choice: 1
Operation: multiply
```

### Expected in Client:
```
Unknown operation. Choose: add | factorial | reverse
```

The client validates input before even calling the master.

---

## Test 8 — Stress Test (Concurrent Overload)

**Goal:** Fire 20 tasks simultaneously and verify system stability under load.

### Steps:

1. Make sure both workers and master are running
2. Run from any machine:

```bash
python stress_test.py
```

### Expected Output:
```
======================================================================
  STRESS TEST — Firing 20 tasks simultaneously
  Target master: localhost:9000
  Client ID: StressTest_c4d1f8a3
======================================================================
  #  0 | factorial  | COMPLETED  | Result: 1
  #  1 | add        | COMPLETED  | Result: 15
  #  2 | reverse    | COMPLETED  | Result: 2sserts
  ...

======================================================================
  RESULTS SUMMARY
======================================================================
  Total tasks    : 20
  Completed      : 20
  Failed         : 0
  Time taken     : 2.41 seconds
======================================================================
```

### Verify via Admin:
```
Choice: 4   (View client summary)
```
Expected: A `StressTest_c4d1f8a3` client with 20 tasks listed.

---

## Test 9 — Dynamic Worker Join (Service Discovery)

**Goal:** Start a 3rd worker mid-session and verify it immediately receives tasks.

### Steps:

1. With registry, master, Worker1, and Worker2 running, open a new terminal:
```
python worker.py 8003
```

2. Check registry log:
```
[10:45:10] [Registry] + Registered Worker3 at localhost:8003
```

3. Submit 3 tasks in the client — they should distribute across all 3 workers.

4. Verify with admin:
```
Choice: 3   (View cluster status)
```

Expected:
```
  Active workers : 3
    • Worker1@localhost:8001
    • Worker2@localhost:8002
    • Worker3@localhost:8003
```

**Key point:** Worker3 was added without restarting the master, editing config.py, or doing anything except running `python worker.py 8003`.

---

## Test 10 — Heartbeat-Based Removal (Crash Detection)

**Goal:** Kill a worker forcefully (not Ctrl+C) and verify the registry reaps it after the heartbeat timeout.

### Steps:

1. Find Worker1's terminal and **close the terminal window entirely** (or use `taskkill /F /PID <pid>` on Windows)
   - This prevents the clean deregister
2. Watch the **Registry log**

### Expected in Registry (after ~10 seconds):
```
[10:48:20] [Registry] ! Reaped Worker1 at localhost:8001 (no heartbeat for 10s)
```

3. Submit a task — it should go to Worker2 (Worker1 is no longer in the pool)

4. Verify via admin → Cluster status: Only Worker2 (and Worker3 if still running) listed.

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
[10:50:05] [AutoScaler] Scaling UP — spawning Worker1 on port 8001
[10:50:05] [AutoScaler] Worker1 spawned (PID: 12345)
[10:50:10] [AutoScaler] Scaling UP — spawning Worker2 on port 8002
[10:50:10] [AutoScaler] Worker2 spawned (PID: 12346)
```

5. Run `stress_test.py` — all tasks should complete across auto-spawned workers

6. Verify via admin → Cluster status:
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
[10:51:45] [AutoScaler] Scaling DOWN — terminating Worker3 (PID: 12347)
[10:51:45] [AutoScaler] Worker3 terminated
```

3. Auto-scaler will NOT go below MIN_WORKERS (2). So Worker1 and Worker2 should remain.

4. Verify via admin → Cluster status.

---

## Test 13 — Admin Dashboard (Full Visibility)

**Goal:** Verify all 4 admin options show correct data.

### Steps:

Run `python admin.py` on the master machine and test each option:

**Option 1 — View all tasks:**
```
Choice: 1
```
Expected: Table showing all tasks with ID, type, status, worker, client, result.

**Option 2 — Check task status:**
```
Choice: 2
Task ID: 101
```
Expected: Full details for task 101 (type, input, status, worker, client, result).

**Option 3 — Cluster status:**
```
Choice: 3
```
Expected: Worker list, task counts, auto-scaler state.

**Option 4 — Client summary:**
```
Choice: 4
```
Expected: All clients who submitted tasks with per-client task counts.

---

## Test 14 — RPC Transparency Verification

**Goal:** Verify the client has absolutely no internal system knowledge.

### Check these points:

| What the client should NOT show | Verified? |
|--------------------------------|-----------|
| Task IDs (e.g., 101, 102) | ☐ |
| Worker IDs (e.g., Worker1, Worker2) | ☐ |
| Cluster status option in menu | ☐ |
| Check task status option in menu | ☐ |
| Other clients' results | ☐ |
| The word "RPC" anywhere in client output | ☐ |

The client menu should show only:
```
Options:
  1. Compute
  2. View past results
  3. Exit
```

Computation output should show only:
```
  10 + 20 = 30
  factorial(5) = 120
  reverse("hello") = "olleh"
```

---

## Quick Reference: All Test Cases

| Test | What It Tests | Expected Outcome |
|------|--------------|--------------------||
| 1 | Single factorial task | Client: `factorial(5) = 120` |
| 2 | 4 tasks round-robin | Alternates Worker1/Worker2 (visible in admin) |
| 3 | Client isolation | Each client sees only own results |
| 4 | Worker1 killed (Ctrl+C) | Client gets result seamlessly; failover to Worker2 |
| 5 | Both workers killed | Client: "Computation failed. Please try again later." |
| 6 | Worker restarted | Re-registers; system resumes normally |
| 7 | Invalid task type | Client rejects, no crash |
| 8 | 20 concurrent tasks | All complete, summary shown |
| 9 | 3rd worker joins mid-session | Auto-discovered, receives tasks immediately |
| 10 | Worker killed forcefully | Registry reaps after 10s heartbeat timeout |
| 11 | Auto-scaling up | Master spawns workers when demand exceeds capacity |
| 12 | Auto-scaling down | Idle auto-spawned workers terminated after 30s |
| 13 | Admin dashboard | All 4 options show correct, complete data |
| 14 | RPC transparency | Client shows no internal details whatsoever |

---

## Task IDs Reference

Task IDs start at 101 and increment by 1 per submission. These are **only visible in the admin dashboard and master logs**, never to the client.
- 1st task = ID 101
- 2nd task = ID 102
- etc.
