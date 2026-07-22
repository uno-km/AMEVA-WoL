# AMEVA-WoL Telegram Setup Guide

This document describes the step-by-step procedure for configuring Telegram Bot API credentials, identifying user identifiers, and configuring target host machines.

---

## 1. Telegram Client Installation

Command transmission requires an active Telegram client interface.

- **Mobile (Android / iOS)**: Install Telegram via official application stores.
- **Desktop (Windows / macOS / Linux)**: Download the desktop binary from [desktop.telegram.org](https://desktop.telegram.org).
- Complete phone number verification to establish account identity.

---

## 2. Telegram Bot Registration via @BotFather

Telegram bots operate using dedicated API tokens issued by the official bot management interface.

1. Locate the official `@BotFather` account within the Telegram search interface.
2. Issue the `/newbot` command.
3. Specify the display name when prompted (e.g. `AMEVA Gateway`).
4. Specify the bot username when prompted. The username MUST terminate with `bot` (e.g. `ameva_wol_gateway_bot`).
5. Copy the issued HTTP API token upon completion.

> **Security Warning**: The API token grants full control over the bot interface. Treat tokens as sensitive credentials. Do not commit or expose token strings.

Example token format: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken`

---

## 3. Telegram User Identifier Verification

To prevent unauthorized command execution, AMEVA-WoL enforces whitelist authorization. Each user possesses a unique numeric identifier.

1. Search for `@userinfobot` or `@raw_data_bot` in Telegram.
2. Issue the `/start` command.
3. Record the returned numeric `Id` field (e.g., `123456789`).

---

## 4. Environment Verification via Diagnostic Auditor

AMEVA-WoL includes automated diagnostic scripts to verify OS compatibility, Python versioning, dependency presence, configuration parameters, data directory permissions, and network reachability.

- **Termux / Linux**:
  ```bash
  bash scripts/check-environment.sh
  ```
- **Windows**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\scripts\check-environment.ps1
  ```

If validation fails, the auditor outputs precise heuristic remediation instructions.

---

## 5. Configuration & Application Execution

### Configuration Setup
Create a `.env` file within the repository root directory:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken
ALLOWED_USER_IDS=123456789
DEFAULT_BROADCAST=192.168.0.255
DEFAULT_WOL_PORT=9
LOG_LEVEL=INFO
DATA_DIR=./data
```

### Execution Modes
- **Default Mode** (Telegram command dispatcher only):
  ```bash
  python -m ameva_wol
  ```
- **Always-On Mode** (Periodic ping keep-alive monitoring and automated wake):
  ```bash
  python -m ameva_wol --always-on 5
  ```

---

## 6. Command Reference

Issue commands directly within the registered Telegram bot chat window:

1. **Register Host**: `/add <alias> <mac> [ip] [broadcast] [port]`
   ```text
   /add desktop AA:BB:CC:DD:EE:01 192.168.0.100
   ```
2. **Transmit Wake-on-LAN**: `/wake <alias>` or `/wake all`
   ```text
   /wake desktop
   ```
3. **Verify Host Reachability**: `/status <alias>` or `/status all`
   ```text
   /status desktop
   ```
4. **List Registered Devices**: `/list`
5. **Unregister Host**: `/remove <alias>`
   ```text
   /remove desktop
   ```
