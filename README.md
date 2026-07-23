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
    A[Telegram Cloud API]

    subgraph Gateway ["Local Gateway Node (Termux / Linux)"]
        direction TB
        B[AMEVA-WoL Core Engine]
        C[(devices.json Registry)]
        D[Always-On Scheduler]
        
        B <--> C
        B --- D
    end

    subgraph Targets ["Target Systems (LAN)"]
        direction TB
        E[Workstation PC]
        F[Server Node]
        G[Storage Appliance]
    end

    A <-->|HTTPS Long Polling| B
    D -.->|ICMP Reachability Ping| Targets
    B ==>|UDP Magic Packet Broadcast| E
    B ==>|UDP Magic Packet Broadcast| F
    B ==>|UDP Magic Packet Broadcast| G
```

---

## Quick Start

### 📱 1. Termux (Android) 왕초보 가이드 (복사&붙여넣기)

**1단계: 터뮤즈 패키지 설치 및 소스코드 다운로드**
터뮤즈를 실행하고 아래 코드를 통째로 복사해서 붙여넣으세요.
```bash
pkg update -y && pkg upgrade -y
pkg install python git -y

git clone https://github.com/uno-km/AMEVA-WoL.git
cd AMEVA-WoL

python -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

**2단계: 환경설정(.env) 파일 만들기**
아래 상자 안의 `{여기에_봇_토큰_입력}`과 `{여기에_내_텔레그램_ID_입력}` 부분을 본인 정보로 바꾼 뒤, **전체 코드를 복사해서 터뮤즈에 붙여넣고 엔터**를 치세요.

```bash
cat << 'EOF' > .env
TELEGRAM_BOT_TOKEN={여기에_봇_토큰_입력}
ALLOWED_USER_IDS={여기에_내_텔레그램_ID_입력}
DEFAULT_BROADCAST=192.168.0.255
DEFAULT_WOL_PORT=9
LOG_LEVEL=INFO
DATA_DIR=./data
EOF
```
*(봇 토큰과 ID를 모른다면 [Telegram Setup Guide](docs/telegram_setup_guide.md)를 참고하세요.)*

**3단계: 봇 실행하기**
```bash
python -m ameva_wol
```

---

### 💻 2. Windows / Linux 일반 설치 가이드

**Installation**
```bash
git clone https://github.com/uno-km/AMEVA-WoL.git
cd AMEVA-WoL

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt
```

**Configuration Setup**
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
| `/host` | `/host` | Retrieve detailed system info (CPU, RAM, GPS, Sensors, Network speed) |
| `/add` | `/add [--overwrite] <alias> <mac> [ip] [broadcast] [port]` | Register or update target device entry |
| `/wake` | `/wake [alias\|all]` | Transmit Magic Packet to specified target or all hosts |
| `/status` | `/status [alias\|all]` | Execute ICMP reachability check (Does not send WoL) |
| `/list` | `/list` | Output compact list of registered devices |
| `/remove` | `/remove <alias>` | Unregister specified target device |

---

## System Deployment

### Termux / Android Boot Setup
Refer to `deploy/termux/start-ameva-wol.sh` for boot initialization details.

### Systemd Service Configuration
Service templates are provided under `deploy/systemd/`:
- User service: `deploy/systemd/ameva-wol-user.service`
- System service: `deploy/systemd/ameva-wol.service`

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
