# AMEVA-WoL

> Lightweight, Secure Telegram-Controlled Wake-on-LAN Gateway for Termux and Linux

---

## Overview

AMEVA-WoL is an unprivileged Wake-on-LAN (WoL) gateway engine designed for continuous deployment on Android (Termux) and Linux host machines. Command processing operates strictly via outbound Telegram Bot API long polling without exposing inbound network ports, HTTP listeners, or requiring router port forwarding.

For step-by-step bot creation, user authorization setup, and host configuration, consult the [Telegram Setup Guide](docs/telegram_setup_guide.md).

---

## Technical Specifications

- **Low Overhead**: Idle CPU footprint < 0.1%, RAM consumption ~25–40 MB.
- **Zero Inbound Network Exposure**: Outbound long polling over HTTPS eliminates public IP requirements, port forwarding, and web servers.
- **Security Posture**:
  - Command execution restricted to whitelisted Telegram User IDs (`ALLOWED_USER_IDS`) and Chat IDs (`ALLOWED_CHAT_IDS`).
  - Subprocess calls (`ping`) execute using explicit argument vectors (`shell=False`). Dynamic string evaluation (`eval`/`exec`) is omitted.
  - Secret tokens are redacted dynamically from loggers and exception tracebacks.
  - Unprivileged execution posture (root/sudo is neither required nor requested).
- **Atomic Data Persistence**: Device registry writes (`data/devices.json`) execute using temporary file buffers, `os.fsync()`, atomic replacement, and restricted `0600` file permissions.
- **Single-Instance Enforcement**: Process locking (`.lock`) prevents concurrent execution instances over identical data directories.
- **Always-On Automated Monitoring**: Optional background scheduler pings registered IP targets periodically and transmits Magic Packets upon host reachability failure.

---

## Architecture Diagram

```mermaid
flowchart TD
    subgraph Telegram Cloud
        TG[Telegram API]
    end

    subgraph Local Area Network
        subgraph Gateway Node
            BOT[AMEVA-WoL Core]
            REG[(devices.json)]
            LOCK[Instance Lock]
            SCHED[Always-On Scheduler]
        end

        subgraph Target Systems
            PC1[Workstation PC]
            PC2[Server Node]
            NAS[Storage Appliance]
        end
    end

    TG <-->|HTTPS Long Polling| BOT
    BOT <--> REG
    BOT --- LOCK
    SCHED -->|ICMP Reachability Check| Target Systems
    BOT -->|UDP Magic Packet Broadcast| PC1
    BOT -->|UDP Magic Packet Broadcast| PC2
    BOT -->|UDP Magic Packet Broadcast| NAS
```

---

## Quick Start

### 1. Installation
```bash
git clone https://github.com/uno-km/AMEVA-WoL.git
cd AMEVA-WoL

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configuration Setup
Create a `.env` configuration file in the repository root directory:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken
ALLOWED_USER_IDS=123456789
DEFAULT_BROADCAST=192.168.0.255
DEFAULT_WOL_PORT=9
LOG_LEVEL=INFO
DATA_DIR=./data
```

### 3. Automated Diagnostic Audit
Execute the system diagnostic script to perform an A-to-Z environment verification:

- **Termux / Linux**: `bash scripts/check-environment.sh`
- **Windows**: `powershell -ExecutionPolicy Bypass -File .\scripts\check-environment.ps1`

Python configuration check:
```bash
python -m ameva_wol --check-config
```

### 4. Execution Modes
- **Default Mode** (Telegram command processing only):
  ```bash
  python -m ameva_wol
  ```
- **Always-On Mode** (Telegram polling + 5-minute periodic ping & keep-alive wake):
  ```bash
  python -m ameva_wol --always-on 5
  ```

---

## Command Reference

| Command | Syntax / Parameters | Description |
| :--- | :--- | :--- |
| `/start` | `/start` | Display authorization status and command summary |
| `/how` | `/how` | Display operational documentation and network constraints |
| `/id` | `/id` | Display requesting Telegram User ID and Chat ID |
| `/add` | `/add [--overwrite] <alias> <mac> [ip] [broadcast] [port]` | Register or update target device entry |
| `/wake` | `/wake [alias\|all]` | Transmit Magic Packet to specified target or all hosts |
| `/status` | `/status [alias\|all]` | Execute ICMP reachability check (Does not send WoL) |
| `/list` | `/list` | Output compact list of registered devices |
| `/remove` | `/remove <alias>` | Unregister specified target device |

---

## System Deployment

### Termux / Android Boot Setup
Refer to `termux/start-ameva-wol.sh` for boot initialization details.

### Systemd Service Configuration
Service templates are provided under `systemd/`:
- User service: `systemd/ameva-wol-user.service`
- System service: `systemd/ameva-wol.service`

---

## Testing

Run unit tests via `pytest`:
```bash
pytest -q
pytest --cov=ameva_wol --cov-report=term-missing
```

---

## License

MIT License. Refer to [LICENSE](LICENSE) for terms.
