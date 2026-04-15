# Deployment Guide — RPC Distributed Task Execution System

A step-by-step guide to run the project **locally on one machine** and **across multiple devices** (Windows ↔ Mac) on the same WiFi/LAN network.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Part 1 — Running Locally (Single Machine)](#part-1--running-locally-single-machine)
3. [Part 2 — Multi-Device Setup (LAN)](#part-2--multi-device-setup-lan)
   - [Finding Your IP Address](#step-1--find-each-machines-lan-ip)
   - [Case 1: Windows Host + Mac/Windows Workers](#case-1-windows-host--macwindows-workers)
   - [Case 2: Mac Host + Windows Workers](#case-2-mac-host--windows-workers)
4. [Firewall Configuration](#firewall-configuration)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.6+** installed on every machine
  - Windows: Download from [python.org](https://python.org) — check "Add Python to PATH" during install
  - Mac: Comes pre-installed as `python3`. Verify: `python3 --version`
- **Same WiFi / LAN network** — all machines must be connected to the same network
- **No external packages needed** — the project uses only Python standard library
- **Project files** copied to every machine (clone the repo or copy the folder)

---

## Part 1 — Running Locally (Single Machine)

This is the simplest setup. Everything runs on `localhost`.

### Step 1 — Verify config.py

Make sure `config.py` has localhost settings:

```python
MASTER_IP   = "localhost"
REGISTRY_IP = "localhost"
```

### Step 2 — With Auto-Scaling ON (Recommended, Minimal Setup)

Open **3 terminals** in the project folder:

```
┌─────────────────────────────────────────────────────────────┐
│  Terminal 1 — Registry                                       │
│  > python registry.py                                        │
│                                                              │
│  Expected output:                                            │
│  [15:30:01] [Registry] Heartbeat reaper started (timeout: 10s)│
│  [15:30:01] [Registry] Service Discovery running on 0.0.0.0:7000│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Terminal 2 — Master (auto-spawns workers)                    │
│  > python master.py                                          │
│                                                              │
│  Expected output:                                            │
│  [15:30:05] [AutoScaler] Started (min=2, max=6, ...)         │
│  [15:30:05] [Master] Running on 0.0.0.0:9000                 │
│  [15:30:10] [AutoScaler] Scaling UP — spawning Worker1 on 8001│
│  [15:30:10] [AutoScaler] Scaling UP — spawning Worker2 on 8002│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Terminal 3 — Client                                         │
│  > python client.py                                          │
│                                                              │
│  =============================================               │
│         Distributed Computation Client                       │
│  =============================================               │
│  Options:                                                    │
│    1. Compute                                                │
│    2. View past results                                      │
│    3. Exit                                                   │
└─────────────────────────────────────────────────────────────┘
```

**Optional — Admin Dashboard (Terminal 4):**
```
> python admin.py
```

### Step 3 — With Auto-Scaling OFF (Manual Workers)

Set `AUTO_SCALE = False` in `config.py`, then open **5 terminals**:

```
Terminal 1:  python registry.py
Terminal 2:  python worker.py 8001
Terminal 3:  python worker.py 8002
Terminal 4:  python master.py
Terminal 5:  python client.py
```

**Optional — Admin Dashboard (Terminal 6):**
```
Terminal 6:  python admin.py
```

### Step 4 — Test It

In the client:
```
Choice: 1
Operation: add
First number : 10
Second number: 20

  10 + 20 = 30
```

In the admin:
```
Choice: 3   (View cluster status)

  Active workers : 2
    • Worker1@localhost:8001
    • Worker2@localhost:8002
```

✅ **Local setup complete!**

---

## Part 2 — Multi-Device Setup (LAN)

### Overview

You need at minimum **2 machines** on the same WiFi. The roles are:

| Role | What runs on it | Can run on same machine? |
|------|----------------|--------------------------|
| **Registry** | `registry.py` | Yes (usually same as Master) |
| **Master** | `master.py` + `admin.py` | Yes (the "host" machine) |
| **Worker** | `worker.py` | Yes (can also be on host) |
| **Client** | `client.py` | Yes (can be anywhere) |

**Typical setup:** Registry + Master + Admin on the **host machine**, Workers on **friend's machines**, Client on **any machine**.

---

### Step 1 — Find Each Machine's LAN IP

Every machine needs to know the host's IP address.

**On Windows:**
```
> ipconfig
```
Look for **IPv4 Address** under your WiFi adapter:
```
Wireless LAN adapter Wi-Fi:
   IPv4 Address. . . . . . . . . : 192.168.1.100    ← THIS
```

**On Mac:**
```
$ ifconfig en0
```
Look for **inet**:
```
inet 192.168.1.101 netmask 0xffffff00 broadcast 192.168.1.255
       ↑ THIS
```

**Alternative (Mac):**
```
$ ipconfig getifaddr en0
192.168.1.101
```

> Write down every machine's IP. You'll need the **host machine's IP** on every device.

---

### Step 2 — Edit config.py on EVERY Machine

Replace both IPs with the **host machine's LAN IP**:

```python
MASTER_IP   = "192.168.1.100"    # ← Host machine's IP (same on ALL machines)
REGISTRY_IP = "192.168.1.100"    # ← Host machine's IP (same on ALL machines)
```

> **Critical:** The same `config.py` values must be used on every machine. If the host is `192.168.1.100`, every machine's config.py should have that IP.

---

### Step 3 — Open Firewall Ports

See the [Firewall Configuration](#firewall-configuration) section below for detailed instructions.

---

### Case 1: Windows Host + Mac/Windows Workers

**Scenario:** Your Windows PC is the host (registry + master + admin). Friends' Macs and/or Windows PCs are workers. Client can run from any machine.

```
Your Windows PC (192.168.1.100):  Registry + Master + Admin
Friend 1's Mac (192.168.1.101):  Worker
Friend 2's Windows (192.168.1.102):  Worker
Any machine:  Client
```

#### On Your Windows PC (Host — 192.168.1.100):

Edit `config.py`:
```python
MASTER_IP   = "192.168.1.100"
REGISTRY_IP = "192.168.1.100"
```

Open **3 terminals** (Command Prompt or PowerShell):

```powershell
# Terminal 1 — Registry
python registry.py

# Terminal 2 — Master
python master.py

# Terminal 3 — Admin Dashboard
python admin.py
```

> **Important:** If `AUTO_SCALE = True`, the master will auto-spawn workers on your Windows PC too. These local workers work alongside the remote ones.

#### On Friend 1's Mac (Worker — 192.168.1.101):

1. Copy the project folder to the Mac (USB, AirDrop, `git clone`, etc.)

2. Edit `config.py`:
```python
MASTER_IP   = "192.168.1.100"    # Host's IP
REGISTRY_IP = "192.168.1.100"    # Host's IP
```

3. Open Terminal and run:
```bash
cd /path/to/RPC_communication
python3 worker.py 8001 --host 192.168.1.101
```

> **`--host 192.168.1.101`** tells the registry the Mac's real LAN IP, so the master can reach it over the network. Without `--host`, it registers as `localhost` which won't work across machines.

Expected output:
```
[15:35:10] [Worker1] Registered with registry at 192.168.1.100:7000
[15:35:10] [Worker1] Heartbeat thread started (interval: 3s)
[15:35:10] [Worker1] Running on 0.0.0.0:8001. Waiting for tasks...
```

#### On Friend 2's Windows PC (Worker — 192.168.1.102):

1. Copy the project folder

2. Edit `config.py`:
```python
MASTER_IP   = "192.168.1.100"    # Host's IP
REGISTRY_IP = "192.168.1.100"    # Host's IP
```

3. Open Command Prompt:
```cmd
cd C:\path\to\RPC_communication
python worker.py 8002 --host 192.168.1.102
```

#### On Any Machine (Client):

1. Edit `config.py` with the host's IP (same as above)
2. Run:
```bash
# Windows:
python client.py

# Mac:
python3 client.py
```

#### Verify (Admin Dashboard on Host):

```
Choice: 3   (View cluster status)

  Active workers : 2
    • Worker1@192.168.1.101:8001     ← Friend 1's Mac
    • Worker2@192.168.1.102:8002     ← Friend 2's Windows
  Pending tasks  : 0
  Completed      : 0
  Auto-scaling   : ON (2-6)
```

Submit a task from any client → it gets sent to one of the remote workers → result comes back!

---

### Case 2: Mac Host + Windows Workers

**Scenario:** Your Mac is the host (registry + master + admin). Friends' Windows PCs are workers.

```
Your Mac (192.168.1.101):  Registry + Master + Admin
Friend 1's Windows (192.168.1.100):  Worker
Friend 2's Windows (192.168.1.102):  Worker
Any machine:  Client
```

#### On Your Mac (Host — 192.168.1.101):

Edit `config.py`:
```python
MASTER_IP   = "192.168.1.101"
REGISTRY_IP = "192.168.1.101"
```

Open **3 Terminal tabs**:

```bash
# Tab 1 — Registry
python3 registry.py

# Tab 2 — Master
python3 master.py

# Tab 3 — Admin Dashboard
python3 admin.py
```

#### On Friend 1's Windows PC (Worker — 192.168.1.100):

1. Copy the project folder to the Windows PC

2. Edit `config.py`:
```python
MASTER_IP   = "192.168.1.101"    # Mac host's IP
REGISTRY_IP = "192.168.1.101"    # Mac host's IP
```

3. Open Command Prompt or PowerShell:
```cmd
cd C:\path\to\RPC_communication
python worker.py 8001 --host 192.168.1.100
```

Expected output:
```
[15:40:05] [Worker1] Registered with registry at 192.168.1.101:7000
[15:40:05] [Worker1] Running on 0.0.0.0:8001. Waiting for tasks...
```

#### On Friend 2's Windows PC (Worker — 192.168.1.102):

Same as Friend 1, but use port `8002`:
```cmd
python worker.py 8002 --host 192.168.1.102
```

#### On Any Machine (Client):

```bash
# Mac:
python3 client.py

# Windows:
python client.py
```

#### Verify (Admin on Mac):

```
Choice: 3

  Active workers : 2
    • Worker1@192.168.1.100:8001     ← Friend 1's Windows
    • Worker2@192.168.1.102:8002     ← Friend 2's Windows
```

---

## Firewall Configuration

Firewalls can block the network connections between machines. You need to allow the specific ports.

### Windows Firewall

**Method 1 — GUI:**
1. Open **Windows Defender Firewall with Advanced Security**
   - Press `Win + R`, type `wf.msc`, press Enter
2. Click **Inbound Rules** → **New Rule...**
3. Select **Port** → Next
4. Select **TCP**, enter the port number → Next
   - Registry machine: `7000`
   - Master machine: `9000`
   - Worker machine: `8001` (or whichever port you're using)
5. Select **Allow the connection** → Next
6. Check all profiles (Domain, Private, Public) → Next
7. Name it (e.g., "RPC Registry 7000") → Finish

**Method 2 — Command Line (PowerShell as Admin):**
```powershell
# On the host machine (registry + master):
netsh advfirewall firewall add rule name="RPC Registry" dir=in action=allow protocol=TCP localport=7000
netsh advfirewall firewall add rule name="RPC Master" dir=in action=allow protocol=TCP localport=9000

# On a worker machine:
netsh advfirewall firewall add rule name="RPC Worker" dir=in action=allow protocol=TCP localport=8001
```

**Method 3 — Quick (for demo only, NOT recommended for regular use):**
```powershell
# Disable firewall entirely (run PowerShell as Admin):
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# Re-enable after demo:
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
```

### Mac Firewall

**Method 1 — Allow Python through firewall:**
```bash
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add $(which python3)
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp $(which python3)
```

**Method 2 — Disable firewall temporarily (for demo):**
1. Open **System Preferences** → **Security & Privacy** → **Firewall**
2. Click the lock icon (bottom-left) and enter your password
3. Click **Turn Off Firewall**
4. After the demo, turn it back on

**Method 3 — Verify firewall status:**
```bash
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
```

---

## Troubleshooting

### Problem: "Connection refused" when starting worker

**Cause:** Registry is not running or the IP in `config.py` is wrong.

**Fix:**
1. Make sure `registry.py` is running first
2. Verify `REGISTRY_IP` in `config.py` matches the registry machine's actual LAN IP
3. Test connectivity: `ping 192.168.1.100` from the worker machine

---

### Problem: Worker registers but tasks fail with timeout

**Cause:** The worker registered with the wrong `--host` value, so the master tries to connect to the wrong IP.

**Fix:**
```bash
# WRONG — worker registers as "localhost" which the master can't reach remotely:
python worker.py 8001

# CORRECT — worker tells the registry its real LAN IP:
python worker.py 8001 --host 192.168.1.101
```

---

### Problem: "python" is not recognized (Windows)

**Fix:** Use the full path or try `python3`:
```cmd
py worker.py 8001 --host 192.168.1.100
```
Or reinstall Python and check "Add Python to PATH".

---

### Problem: "python" runs Python 2 on Mac

**Fix:** Always use `python3` on Mac:
```bash
python3 worker.py 8001 --host 192.168.1.101
```

---

### Problem: Machines can't ping each other

**Cause:** They're on different networks or WiFi isolation is enabled.

**Fix:**
1. Make sure all machines are on the **same WiFi network** (same SSID)
2. Some public WiFi networks isolate devices — use a personal hotspot or home WiFi
3. Test with: `ping 192.168.1.100` from each machine

---

### Problem: Workers show up in admin but auto-spawned workers aren't working on remote tasks

**Cause:** Auto-spawned workers only run on the **master's machine** (spawned via `subprocess`). They register as `localhost` and can't be reached by remote masters.

**Fix:** This is expected behavior. Auto-scaling only works for local workers. Remote workers must be started manually with `--host`.

---

### Problem: Admin shows "Auto-spawned: Worker1, Worker2" but I started workers manually

**Cause:** `AUTO_SCALE = True` and `MIN_WORKERS = 2`, so the master auto-spawned workers even though you started some manually.

**Fix:** Either:
- Set `AUTO_SCALE = False` if you want full manual control
- Or set `MIN_WORKERS = 1` to reduce auto-spawning
- Or just leave it — auto-spawned and manual workers coexist fine

---

## Quick Reference — Commands by OS

### Windows (Command Prompt or PowerShell)

```cmd
cd C:\path\to\RPC_communication

:: Host machine
python registry.py
python master.py
python admin.py

:: Worker machine
python worker.py 8001 --host YOUR_WINDOWS_IP

:: Client (any machine)
python client.py

:: Stress test
python stress_test.py
```

### Mac (Terminal)

```bash
cd /path/to/RPC_communication

# Host machine
python3 registry.py
python3 master.py
python3 admin.py

# Worker machine
python3 worker.py 8001 --host YOUR_MAC_IP

# Client (any machine)
python3 client.py

# Stress test
python3 stress_test.py
```

---

## Startup Order

The correct startup order is:

```
1. registry.py     ← ALWAYS FIRST (workers and master need it)
2. master.py       ← SECOND (connects to registry, starts auto-scaler)
3. worker.py       ← THIRD (registers with registry)
                      (skip if AUTO_SCALE = True — master spawns them)
4. client.py       ← ANYTIME (connects to master)
5. admin.py        ← ANYTIME (connects to master, run on host machine)
```

> Workers can be started before or after the master — they register with the registry independently. But the registry must be running first.

---

## Summary Table

| Setup | Terminals Needed | config.py IPs |
|-------|-----------------|---------------|
| Local (auto-scale ON) | 3 (registry, master, client) + optional admin | `localhost` |
| Local (auto-scale OFF) | 5 (registry, 2 workers, master, client) + optional admin | `localhost` |
| Multi-device | 1 per machine | Host machine's LAN IP on ALL machines |
