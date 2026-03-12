# Testing Guide — RPC Distributed Task Execution System

## Setup

### Option A — Single Machine (Local Testing)

Keep `config.py` as-is (all `localhost`). Open 4 terminals:

```
Terminal 1:  python worker.py 8001
Terminal 2:  python worker.py 8002
Terminal 3:  python master.py
Terminal 4:  python client.py
```

### Option B — Multi-Machine (Real Distributed, Same WiFi)

1. Edit `config.py` on **all machines** with actual LAN IPs:
   ```python
   MASTER_IP = "192.168.x.x"    # IP of PC running master.py
   WORKERS = [
       {"id": "Worker1", "host": "192.168.x.x", "port": 8001},   # Worker1 machine IP
       {"id": "Worker2", "host": "192.168.x.x", "port": 8002},   # Worker2 machine IP
   ]
   ```
2. Each machine clones the repo and edits `config.py` with the same IPs
3. Allow firewall ports: 9000 (master), 8001 (Worker1), 8002 (Worker2)
    Windows Defender Firewall → Advanced Settings
    → Inbound Rules → New Rule → Port → TCP → 9000 → Allow

    For Mac
      sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add python3
      # or just turn off Mac Firewall temporarily for demo:
      System Preferences → Security & Privacy → Firewall → Turn Off

Then run on each machine:
```
# Friend 1's machine (Windows):
python worker.py 8001

# Friend 2's machine (Mac):
python3 worker.py 8002

# Your machine:
python master.py

# Client — run from any machine:
python client.py
```

---

Wait until you see:
- `[HH:MM:SS] [Worker1] Running on 0.0.0.0:8001 (accepting connections from any machine). Waiting for tasks...`
- `[HH:MM:SS] [Worker2] Running on 0.0.0.0:8002 (accepting connections from any machine). Waiting for tasks...`
- `[HH:MM:SS] [Master] Running on 0.0.0.0:9000 (clients connect via <MASTER_IP>:9000)`

> All log lines include a timestamp `[HH:MM:SS]`. This makes the **5-second fault detection gap visually obvious** during the demo — you can watch the clock jump when a worker is unreachable.

Then run the client and follow the test cases below.

---

## Test 1 — Single Task Execution (Factorial)

**Goal:** Verify a single task runs end-to-end correctly.

### Steps in client (Terminal 4):

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

### Expected Output in Master (Terminal 3):
```
[10:32:41] [Master] Task 101 submitted: factorial([5])
[10:32:41] [Master] Assigning task 101 to Worker1
[10:32:41] [Master] Task 101 → COMPLETED | Result: 120
```

### Expected Output in Worker1 (Terminal 1):
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

1. **Kill Worker1** — go to Terminal 1, press `Ctrl+C`
   - You will see: `[Worker1] Shutting down.` and the process exits cleanly

2. **In the client, submit a new task:**
```
Choice: 1
Task type: add
First number : 100
Second number: 200
```

3. **Wait ~5 seconds** (the master is trying to reach Worker1 and timing out)

### Expected Output in Client:
```
Submitting: add([100, 200]) ...

  Task ID : 105
  Status  : COMPLETED
  Result  : 300
  Worker  : Worker2
```

### Expected Output in Master (Terminal 3):
```
[10:35:10] [Master] Task 105 submitted: add([100, 200])
[10:35:10] [Master] Assigning task 105 to Worker1
[10:35:15] [Master] Worker1 unreachable (...). Trying next worker...   ← 5s gap visible here!
[10:35:15] [Master] Assigning task 105 to Worker2
[10:35:15] [Master] Task 105 → COMPLETED | Result: 300
```

> **KEY DEMO MOMENT:** The timestamps show `10:35:10` → `10:35:15` — a visible 5-second gap. This is the fault detection latency in action. Point to it during your demo and say: *"This 5-second gap is exactly where the system detected the failure and rerouted the task."*

**Key observation:** The task still completes — it was automatically reassigned to Worker2.

---

## Test 5 — All Workers Down

**Goal:** Verify the system fails gracefully when no workers are available.

### Steps:

1. Kill Worker1 (Ctrl+C Terminal 1) if not already done
2. Kill Worker2 (Ctrl+C Terminal 2)
3. Submit a task:

```
Choice: 1
Task type: factorial
Number: 4
```

4. Wait ~10 seconds (master tries both workers, each times out)

### Expected Output in Client:
```
  Task ID : 106
  Status  : FAILED
  Result  : All workers unavailable
  Worker  : None
```

### Expected Output in Master:
```
[10:40:01] [Master] Task 106 submitted: factorial([4])
[10:40:01] [Master] Assigning task 106 to Worker1
[10:40:06] [Master] Worker1 unreachable (...). Trying next worker...   ← 5s gap
[10:40:06] [Master] Assigning task 106 to Worker2
[10:40:11] [Master] Worker2 unreachable (...). Trying next worker...   ← another 5s gap
[10:40:11] [Master] Task 106 FAILED — no available workers
```

---

## Test 6 — Worker Recovery After Restart

**Goal:** Verify workers can restart and resume handling tasks.

### Steps:

1. Restart Worker1:
```
Terminal 1:  python worker.py 8001
```

2. Submit a task in the client:
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

  Tasks per worker:
    Worker1      ██████████  (10 tasks)
    Worker2      ██████████  (10 tasks)
======================================================================
```

**Key observations:**
- Tasks per worker should be split evenly (round-robin working correctly)
- All 20 tasks complete successfully (concurrency handled by ThreadingMixIn)
- Run from multiple machines at once to simulate real overload

### Overload Variant — Kill one worker before running stress test:

Kill Worker1, then run `stress_test.py`. Expected: all 20 tasks route to Worker2 (fault tolerance under load).

---

## Quick Reference: All Test Cases

| Test | What It Tests | Expected Outcome |
|------|--------------|-----------------|
| 1 | Single factorial task | Result: 120, Worker1 |
| 2 | 4 tasks round-robin | Alternates Worker1/Worker2 |
| 3 | Task status tracking | Correct status in table |
| 4 | Worker1 killed mid-session | Task reassigned to Worker2 after 5s |
| 5 | Both workers killed | Status: FAILED gracefully |
| 6 | Worker restarted | System resumes normally |
| 7 | Invalid task type | Client rejects, no crash |
| 8 | 20 concurrent tasks | Even split, all complete, bar chart shown |

---

## Task IDs Reference

Task IDs start at 101 and increment by 1 per submission.
- 1st task = ID 101
- 2nd task = ID 102
- etc.
