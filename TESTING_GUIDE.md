# Testing Guide — RPC Distributed Task Execution System

## Setup: Open 4 Terminal Windows

Before running any test, start the system in this exact order:

```
Terminal 1:  python worker.py 8001
Terminal 2:  python worker.py 8002
Terminal 3:  python master.py
Terminal 4:  python client.py
```

Wait until you see:
- `[Worker1] Running on localhost:8001. Waiting for tasks...`
- `[Worker2] Running on localhost:8002. Waiting for tasks...`
- `[Master] Running on localhost:9000`

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
[Master] Task 101 submitted: factorial([5])
[Master] Assigning task 101 to Worker1
[Master] Task 101 → COMPLETED | Result: 120
```

### Expected Output in Worker1 (Terminal 1):
```
[Worker1] Task 101 received: factorial([5])
[Worker1] Task 101 completed. Result: 120
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
   - You will see: `[Worker1]` terminal closes

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
[Master] Task 105 submitted: add([100, 200])
[Master] Assigning task 105 to Worker1
[Master] Worker1 unreachable (<timeout error>). Trying next worker...
[Master] Assigning task 105 to Worker2
[Master] Task 105 → COMPLETED | Result: 300
```

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
[Master] Task 106 submitted: factorial([4])
[Master] Assigning task 106 to Worker1
[Master] Worker1 unreachable (...). Trying next worker...
[Master] Assigning task 106 to Worker2
[Master] Worker2 unreachable (...). Trying next worker...
[Master] Task 106 FAILED — no available workers
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

## Quick Reference: All Test Cases

| Test | What It Tests | Expected Outcome |
|------|--------------|-----------------|
| 1 | Single factorial task | Result: 120, Worker1 |
| 2 | 4 tasks round-robin | Alternates Worker1/Worker2 |
| 3 | Task status tracking | Correct status in table |
| 4 | Worker1 killed mid-session | Task reassigned to Worker2 |
| 5 | Both workers killed | Status: FAILED gracefully |
| 6 | Worker restarted | System resumes normally |
| 7 | Invalid task type | Client rejects, no crash |

---

## Task IDs Reference

Task IDs start at 101 and increment by 1 per submission.
- 1st task = ID 101
- 2nd task = ID 102
- etc.
