# AMEVA-WoL ⚡

> **Lightweight, Secure, Telegram-Controlled Wake-on-LAN Gateway for Termux & Linux**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)

---

## 📌 Overview

**AMEVA-WoL** is an extremely lightweight, secure, and fast Telegram-controlled Wake-on-LAN (WoL) gateway designed to run continuously on:

1. **Termux on an old rooted/unrooted Samsung Galaxy S7 (or any Android device)**
2. **Low-spec old Linux laptops**
3. **Modern Linux servers and desktop machines**

The gateway phone or laptop remains connected to your local home network (LAN). When you send Telegram commands to the bot, AMEVA-WoL constructs standard 102-byte UDP Magic Packets and broadcasts them over the local network to wake up target computers.

---

## ✨ Key Features

- 🚀 **Extremely Lightweight**: Near-zero idle CPU usage (< 0.1%) and minimal RAM footprint (~25–40 MB).
- 🛡️ **Zero Public Exposure**: Operates exclusively via Telegram Bot API **long polling**. No public IP, dynamic DNS, router port forwarding, or HTTP servers required.
- 🔐 **Security by Default**:
  - Whitelist-restricted command authorization (`ALLOWED_USER_IDS` & `ALLOWED_CHAT_IDS`).
  - No `shell=True` or dynamic code evaluation (`eval`/`exec`). Subprocesses use strict argument lists.
  - Automatic secret token redaction in logs and exception tracebacks.
  - Rate limiting to protect against command spam.
  - Unprivileged execution (Root / `sudo` **NOT** required).
- 💾 **Atomic Persistent Storage**: Device registry (`data/devices.json`) uses atomic temporary writes with `os.fsync()` and restricted `0o600` file permissions to prevent data corruption.
- 🔒 **Process Lock Enforcement**: Single-instance file lock prevents multiple gateway instances from conflicting over the data directory.
- 🕒 **Always-On Monitoring Mode**: Periodic automated keep-alive scheduler pings target computers and transmits Wake-on-LAN packets if a host goes offline.
- 📱 **Termux & Linux Ready**: Includes Termux boot scripts (`termux/start-ameva-wol.sh`) and hardened systemd service units.

---

## 🏗️ Architecture Diagram

```mermaid
flowchart TD
    subgraph Telegram Cloud
        TG[Telegram API]
    end

    subgraph Local Area Network (LAN)
        subgraph Gateway Device (Termux / Linux Laptop)
            BOT[AMEVA-WoL Gateway]
            REG[(devices.json)]
            LOCK[Instance Lock]
            SCHED[Always-On Scheduler]
        end

        subgraph Target Computers
            PC1[Workstation PC]
            PC2[Home Server]
            NAS[Storage NAS]
        end
    end

    TG <-->|Long Polling (HTTPS Outbound Only)| BOT
    BOT <--> REG
    BOT --- LOCK
    SCHED -->|1. ICMP Ping Check| Target Computers
    BOT -->|2. UDP Broadcast Magic Packet (Port 9/7)| PC1
    BOT -->|2. UDP Broadcast Magic Packet (Port 9/7)| PC2
    BOT -->|2. UDP Broadcast Magic Packet (Port 9/7)| NAS
```

---

## 🔒 Security Model & Threat Model

AMEVA-WoL is designed under a **Zero Trust Inbound Network** posture:

1. **No Inbound Ports**: The gateway never opens inbound sockets or HTTP servers. It communicates with Telegram solely over outbound HTTPS long polling.
2. **Strict User Whitelisting**: Every incoming Telegram message is checked against `ALLOWED_USER_IDS`. Unauthorized requests are dropped silently without acknowledging registered device names.
3. **Input Validation**:
   - **Aliases**: Enforces `^[a-z0-9_-]{1,32}$`.
   - **MAC Addresses**: Enforces 12 hex digits; normalizes into uppercase colon format `AA:BB:CC:DD:EE:FF`.
   - **IPv4 Addresses**: Validated strictly via Python's `ipaddress` module.
4. **No Privilege Escalation**: Runs as standard user. Root access is neither required nor recommended.
5. **Physical & Network Security Note**: Anyone with physical access to the gateway phone/laptop or access to your local Wi-Fi/LAN broadcast domain can inspect local hardware or network packets. Ensure your physical hardware and Wi-Fi security (WPA3/WPA2-Enterprise) are properly configured.

---

## 📋 System Requirements

- **Python**: Version **3.10** or newer.
- **Operating System**: Linux (Ubuntu, Debian, Arch, RHEL, Alpine) or Android (Termux).
- **Network**: Wi-Fi or Ethernet connection on the same LAN/subnet as target computers.
- **Dependencies**: `python-telegram-bot` (v20+), `python-dotenv`, `pytest` (for tests).

---

## 🤖 Telegram Bot & Environment Setup

### 1. Create Telegram Bot via BotFather
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the prompts to choose a bot name and username.
3. Copy the HTTP API Access Token provided by BotFather (e.g., `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken`).

### 2. Determine Your Telegram User ID
To ensure only **you** can control the bot, obtain your numeric Telegram User ID:
- Open Telegram and message `@userinfobot` or `@raw_data_bot`.
- Copy your numeric **User ID** (e.g. `123456789`).

> [!TIP]
> Alternatively, start AMEVA-WoL with your user ID in `.env`, send `/id` to your bot, and verify your ID.

---

## 🚀 Quick Start Guide

### 1. Clone & Install
```bash
git clone https://github.com/<OWNER>/AMEVA-WoL.git
cd AMEVA-WoL

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure `.env`
```bash
cp .env.example .env
chmod 600 .env
```
Edit `.env` using your text editor:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken
ALLOWED_USER_IDS=123456789
ALLOWED_CHAT_IDS=
DEFAULT_BROADCAST=192.168.0.255
DEFAULT_WOL_PORT=9
DEFAULT_WOL_REPEAT=3
DEFAULT_WOL_DELAY_MS=250
PING_TIMEOUT_SECONDS=2
LOG_LEVEL=INFO
DATA_DIR=./data
RATE_LIMIT_COMMANDS=10
RATE_LIMIT_WINDOW_SECONDS=60
TELEGRAM_POLL_TIMEOUT_SECONDS=30
```

### 3. Verify Configuration
```bash
python -m ameva_wol --check-config
```

### 4. Run AMEVA-WoL

**Default Mode** (Telegram bot commands only):
```bash
python -m ameva_wol
```

**Always-On Mode** (Telegram commands + periodic host keep-alive check every 5 minutes):
```bash
python -m ameva_wol --always-on 5
```

---

## 📖 Telegram Command Reference

| Command | Description | Example |
| :--- | :--- | :--- |
| `/start` | Show welcome message, authorization status, and quick command summary | `/start` |
| `/how` | Display comprehensive user manual and WoL prerequisites | `/how` |
| `/id` | Show your Telegram User ID and current Chat ID | `/id` |
| `/add` | Register a new target computer (or display usage syntax) | `/add desktop AA:BB:CC:DD:EE:01 192.168.0.100` |
| `/wake` | Transmit Magic Packet to target computer(s) immediately | `/wake desktop` or `/wake all` |
| `/status` | Check ICMP ping reachability (Never sends WoL packets) | `/status desktop` or `/status all` |
| `/list` | Display compact list of registered devices | `/list` |
| `/remove` | Unregister a device by alias | `/remove desktop` |

---

## ➕ Detailed `/add` Syntax & Examples

```text
/add <alias> <mac> <ip>
/add <alias> <mac> <ip> <broadcast>
/add <alias> <mac> <ip> <broadcast> <port>
/add <alias> <mac>
/add --overwrite <alias> <mac> <ip> [broadcast] [port]
```

### Examples:
- **Standard Registration**: `/add workstation AA:BB:CC:DD:EE:01 192.168.0.107`
- **Hyphen MAC Format**: `/add server AA-BB-CC-DD-EE-02 192.168.0.108`
- **No-Delimiter MAC with Port**: `/add nas AABBCCDDEEFF 192.168.0.50 192.168.0.255 9`
- **WoL Only (No IP)**: `/add media-pc AA:BB:CC:DD:EE:03`
  - *Note: WoL will work normally, but `/status` and Always-On checks will skip this device.*
- **Overwrite Alias**: `/add --overwrite workstation AA:BB:CC:DD:EE:99 192.168.0.107`

---

## 🔄 Modes of Operation

### 1. Default Mode (`python -m ameva_wol`)
In default mode, AMEVA-WoL starts Telegram long polling and listens for incoming user commands. It operates passively with near-zero CPU and network overhead until a `/wake` command is received.

### 2. Always-On Mode (`python -m ameva_wol --always-on [MINUTES]`)
In Always-On mode, AMEVA-WoL maintains Telegram polling while running an async background task:
- Every `N` minutes (default: 5 minutes), it pings registered computers with an IP address.
- If a target computer fails to respond to ICMP ping, it automatically transmits Wake-on-LAN Magic Packets.
- Overlapping runs are prevented automatically.
- Logs cycle statistics locally (`data/ameva_wol.log`) without spamming Telegram.

---

## 📱 Termux / Samsung Galaxy S7 Installation Guide

AMEVA-WoL runs seamlessly on an old Galaxy S7 or any Android phone running Termux.

> [!WARNING]
> Do **NOT** use the obsolete Play Store version of Termux. Install the maintained build from [F-Droid](https://f-droid.org/packages/com.termux/).

### Step-by-Step Termux Setup

1. **Update Termux Packages**:
   ```bash
   pkg update && pkg upgrade -y
   ```

2. **Install Core Utilities & Python**:
   ```bash
   pkg install -y python git iputils termux-api
   ```

3. **Clone Repository & Setup Virtual Environment**:
   ```bash
   git clone https://github.com/<OWNER>/AMEVA-WoL.git
   cd AMEVA-WoL
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure Environment & Test**:
   ```bash
   cp .env.example .env
   chmod 600 .env
   # Edit .env with nano or vi
   nano .env

   python -m ameva_wol --check-config
   ```

5. **Acquire Termux Wake-Lock**:
   To prevent Android CPU sleep from suspending AMEVA-WoL:
   ```bash
   termux-wake-lock
   ```
   *(Ensure Termux:API app is installed if prompted).*

6. **Disable Android Battery Optimization**:
   - Go to Android Settings -> Battery -> Battery Optimization.
   - Select **Termux** and set to **"Don't optimize"**.
   - Ensure Wi-Fi option **"Keep Wi-Fi on during sleep"** is set to **Always**.

7. **Setup Automatic Boot with Termux:Boot**:
   - Install **Termux:Boot** from F-Droid.
   - Open Termux:Boot once to grant permissions.
   - Create the boot directory and symlink the startup script:
     ```bash
     mkdir -p ~/.termux/boot
     cp termux/start-ameva-wol.sh ~/.termux/boot/start-ameva-wol.sh
     chmod +x ~/.termux/boot/start-ameva-wol.sh
     ```
   AMEVA-WoL will now automatically boot on phone restart!

---

## 💻 Linux Laptop Deployment Options

### Option 1: Foreground / Debugging
```bash
python -m ameva_wol --always-on 5
```

### Option 2: tmux or screen
```bash
tmux new -s ameva
source .venv/bin/activate
python -m ameva_wol --always-on 5
# Press Ctrl+B then D to detach
```

### Option 3: Systemd User Service (Recommended)
1. Copy user service file:
   ```bash
   mkdir -p ~/.config/systemd/user
   cp systemd/ameva-wol-user.service ~/.config/systemd/user/ameva-wol.service
   ```
2. Enable and start:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now ameva-wol.service
   loginctl enable-linger $USER
   ```

### Option 4: System-Wide Systemd Service
1. Copy repository to `/opt/AMEVA-WoL`.
2. Copy systemd service file:
   ```bash
   sudo cp systemd/ameva-wol.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now ameva-wol.service
   ```

---

## 🧪 Testing & Verification

Run unit tests locally with `pytest`:

```bash
# Run quiet test suite
pytest -q

# Run coverage analysis
pytest --cov=ameva_wol --cov-report=term-missing
```

*Note: All tests use isolated mocks for network sockets, ICMP pings, and Telegram API updates. No network packets are transmitted during tests.*

---

## 🖥️ Target Computer Configuration (BIOS / UEFI / NIC)

For Wake-on-LAN to function, the target computer must be properly configured:

### 1. BIOS/UEFI Settings
- Enter BIOS/UEFI setup on startup (F2, Del, or F12).
- Enable **Wake-on-LAN (WoL)**, **Power On by PCI-E/PME**, or **Resume by LAN**.
- Disable **Deep Sleep**, **ErP/EuP Ready** (which turns off network adapter power standby).

### 2. Windows NIC Adapter Settings
- Open `Device Manager` -> `Network adapters` -> your Ethernet NIC properties.
- **Power Management** tab:
  - Check *Allow this device to wake the computer*.
  - Check *Only allow a magic packet to wake the computer*.
- **Advanced** tab:
  - Enable *Wake on Magic Packet*.
  - Disable *Fast Startup* in Windows Power Options (Fast Startup can prevent WoL in S5 state).

### 3. Linux NIC Settings
Verify WoL is enabled on your target network interface using `ethtool`:
```bash
sudo ethtool eth0 | grep "Wake-on"
# Should display: Wake-on: g
```
If set to `d` (disabled), enable it with:
```bash
sudo ethtool -s eth0 wol g
```

---

## ❓ Frequently Asked Questions (FAQ)

**Q: Does Wake-on-LAN work over Wi-Fi?**  
A: Wake-on-Wireless-LAN (WoWLAN) is supported by some modern Wi-Fi cards, but standard wired Ethernet is vastly more reliable. We recommend target computers use wired Ethernet connections.

**Q: Why does `/status` say OFFLINE when my computer is turned on?**  
A: Some OS firewalls (e.g. Windows Firewall) block incoming ICMP Ping requests by default. Enable "File and Printer Sharing (Echo Request - ICMPv4-In)" in Windows Firewall.

**Q: Can I access the gateway outside my home network?**  
A: Yes! Because command interaction occurs over Telegram, you can send Telegram messages to your bot from anywhere in the world without exposing your home router.

---

## 📄 License

This project is licensed under the terms of the **MIT License**. See the [LICENSE](LICENSE) file for details.
