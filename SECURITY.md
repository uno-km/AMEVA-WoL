# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0.0 | :x:                |

## Reporting a Vulnerability

Security is a fundamental design goal of **AMEVA-WoL**. If you discover a security vulnerability, please report it responsibly.

### Disclosure Instructions
- **Do NOT** open a public issue or discussion on GitHub.
- Email your findings directly to the repository maintainer or security contact.
- Include detailed steps to reproduce the issue, expected vs actual behavior, and potential impact.
- **NEVER** include production Telegram bot tokens, API keys, or live device MAC/IP configurations in reports.

## Hardening & Security Model

1. **Unprivileged Execution**: AMEVA-WoL runs strictly as an unprivileged user process. It does not require `root` or `sudo` privileges.
2. **Access Control**: Commands are restricted strictly to configured Telegram User IDs (`ALLOWED_USER_IDS`) and optional Chat IDs (`ALLOWED_CHAT_IDS`). Unauthorized requests are silently ignored or minimally logged without disclosing registered devices.
3. **No Dynamic Shell Execution**: All subcommands (such as `ping`) are invoked using explicit argument arrays via `subprocess` with `shell=False`. No `eval`, `exec`, or dynamic shell strings are used.
4. **Secret Protection**: Secrets are loaded strictly from `.env` files with `600` permissions. Bot tokens are dynamically redacted from exception tracebacks and logs.
5. **Data Protection**: Device registries are stored in `DATA_DIR/devices.json` with restricted permissions (`0o600`).
6. **Physical & Network Gateway Security**: Anyone with physical access to the device or local broadcast domain can potentially sniff network traffic or access local files. Secure your physical hardware and local network accordingly.
