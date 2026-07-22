# Changelog

All notable changes to the **AMEVA-WoL** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-22

### Added
- Initial production release of AMEVA-WoL gateway.
- Full Telegram Bot API long polling integration with `python-telegram-bot`.
- Command suite: `/start`, `/how`, `/add`, `/wake`, `/status`, `/list`, `/remove`, `/id`.
- Native Python Wake-on-LAN Magic Packet builder over UDP broadcast (`socket` library).
- Configurable Always-On periodic monitoring loop for automated host keep-alive waking.
- Security enforcement: user/chat ID whitelist, secret redaction in exceptions/logs, alias and MAC format validation, sliding-window rate limiting.
- Atomic filesystem updates for `devices.json` to prevent data corruption.
- Process single-instance locking using PID/file lock (`.lock` file in `DATA_DIR`).
- Termux boot integration script (`termux/start-ameva-wol.sh`) and systemd service descriptors (`systemd/`).
- Full unit and integration test suite with high coverage using `pytest`.
