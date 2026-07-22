#!/usr/bin/env bash
# ==============================================================================
# AMEVA-WoL Environment & Setup Diagnostic Auditor (Termux / Linux)
# ==============================================================================
# Performs an A-to-Z audit of OS, Python environment, dependencies, .env file,
# Telegram bot credentials, file permissions, data directory, network connectivity,
# and device registry. Provides heuristic troubleshooting guidance for failed checks.
# ==============================================================================

set -u

# Terminal Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

HEURISTIC_FIXES=()

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    WARN_COUNT=$((WARN_COUNT + 1))
    if [ -n "${2:-}" ]; then
        HEURISTIC_FIXES+=("[WARN] $1\n   -> FIX: $2")
    fi
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    if [ -n "${2:-}" ]; then
        HEURISTIC_FIXES+=("[FAIL] $1\n   -> FIX: $2")
    fi
}

log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

# Determine repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_DIR}" || exit 1

echo -e "${BOLD}${BLUE}==============================================================${NC}"
echo -e "${BOLD}${BLUE}   AMEVA-WoL Environment & Setup Diagnostic Auditor          ${NC}"
echo -e "${BOLD}${BLUE}==============================================================${NC}"
log_info "Repository Path: ${REPO_DIR}"
log_info "Audit Timestamp: $(date -u)"
echo ""

# ------------------------------------------------------------------------------
# 1. OS & Shell Environment Check
# ------------------------------------------------------------------------------
echo -e "${BOLD}1. System Environment Check${NC}"
OS_TYPE="$(uname -s)"
log_pass "Operating System: ${OS_TYPE} ($(uname -m))"

if [ -d "/data/data/com.termux" ]; then
    log_info "Environment: Android Termux detected"
    if command -v termux-wake-lock >/dev/null 2>&1; then
        log_pass "Termux API / wake-lock utility available"
    else
        log_warn "Termux API utility (termux-wake-lock) not found" "Run 'pkg install termux-api' in Termux to prevent CPU sleep during standby."
    fi
fi

# ------------------------------------------------------------------------------
# 2. System Utilities Check (git, ping, python3)
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}2. System Utilities Check${NC}"

if command -v git >/dev/null 2>&1; then
    log_pass "Git binary available: $(git --version | head -n1)"
else
    log_fail "Git binary missing" "Install Git: 'pkg install git' (Termux) or 'sudo apt install git' (Linux)."
fi

if command -v ping >/dev/null 2>&1; then
    log_pass "Ping utility available"
else
    log_fail "Ping utility missing" "Install iputils: 'pkg install iputils' (Termux) or 'sudo apt install iputils-ping' (Linux)."
fi

# ------------------------------------------------------------------------------
# 3. Python 3.10+ Environment Check
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}3. Python Environment Check${NC}"

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

if [ -z "${PYTHON_BIN}" ]; then
    log_fail "Python 3 executable not found in PATH" "Install Python 3.10+: 'pkg install python' (Termux) or 'sudo apt install python3 python3-venv' (Linux)."
else
    PY_VER="$(${PYTHON_BIN} -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
    PY_MAJOR="$(${PYTHON_BIN} -c 'import sys; print(sys.version_info.major)')"
    PY_MINOR="$(${PYTHON_BIN} -c 'import sys; print(sys.version_info.minor)')"

    if [ "${PY_MAJOR}" -eq 3 ] && [ "${PY_MINOR}" -ge 10 ]; then
        log_pass "Python version: ${PY_VER} (>= 3.10)"
    else
        log_fail "Python version is ${PY_VER} (AMEVA-WoL requires Python 3.10+)" "Upgrade Python to 3.10 or newer."
    fi
fi

# ------------------------------------------------------------------------------
# 4. Virtual Environment & Packages Check
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}4. Virtual Environment & Dependencies Check${NC}"

VENV_ACT="false"
if [ -d "${REPO_DIR}/.venv" ]; then
    log_pass "Virtual environment directory (.venv) exists"
    if [ -f "${REPO_DIR}/.venv/bin/activate" ]; then
        source "${REPO_DIR}/.venv/bin/activate"
        PYTHON_BIN="python"
        VENV_ACT="true"
    fi
else
    VENV_FIX_MSG="Create virtual environment & install requirements:\n"
    VENV_FIX_MSG="${VENV_FIX_MSG}      1) Create venv: 'python3 -m venv .venv'\n"
    VENV_FIX_MSG="${VENV_FIX_MSG}      2) Activate:    'source .venv/bin/activate'\n"
    VENV_FIX_MSG="${VENV_FIX_MSG}      3) Install:     'pip install -r requirements.txt'"
    log_warn "Virtual environment (.venv) not found in repository root" "${VENV_FIX_MSG}"
fi

# Check Python libraries
if [ -n "${PYTHON_BIN}" ]; then
    if ${PYTHON_BIN} -c "import telegram" >/dev/null 2>&1; then
        TG_VER="$(${PYTHON_BIN} -c 'import telegram; print(getattr(telegram, "__version__", "Unknown"))')"
        log_pass "python-telegram-bot library installed (v${TG_VER})"
    else
        log_fail "python-telegram-bot library is missing" "Install dependencies: 'pip install -r requirements.txt'."
    fi

    if ${PYTHON_BIN} -c "import dotenv" >/dev/null 2>&1; then
        log_pass "python-dotenv library installed"
    else
        log_fail "python-dotenv library is missing" "Install dependencies: 'pip install -r requirements.txt'."
    fi

    if PYTHONPATH="${REPO_DIR}/src" ${PYTHON_BIN} -c "import ameva_wol" >/dev/null 2>&1; then
        log_pass "AMEVA-WoL package importable (src/ameva_wol)"
    else
        log_fail "AMEVA-WoL package failed to import" "Ensure repository files are intact and PYTHONPATH is configured."
    fi
fi

# ------------------------------------------------------------------------------
# 5. Environment File (.env) Security & Secrets Audit
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}5. .env Configuration Audit${NC}"

ENV_FILE="${REPO_DIR}/.env"
ENV_MANUAL="1) Copy example file: 'cp .env.example .env'\n"
ENV_MANUAL="${ENV_MANUAL}   2) Edit .env and configure the following required variables:\n"
ENV_MANUAL="${ENV_MANUAL}      --------------------------------------------------------\n"
ENV_MANUAL="${ENV_MANUAL}      TELEGRAM_BOT_TOKEN=123456789:ABCdef... (From @BotFather)\n"
ENV_MANUAL="${ENV_MANUAL}      ALLOWED_USER_IDS=123456789              (From @userinfobot)\n"
ENV_MANUAL="${ENV_MANUAL}      DEFAULT_BROADCAST=192.168.0.255         (Subnet Broadcast)\n"
ENV_MANUAL="${ENV_MANUAL}      DEFAULT_WOL_PORT=9                      (UDP Port)\n"
ENV_MANUAL="${ENV_MANUAL}      LOG_LEVEL=INFO                          (Logging Level)\n"
ENV_MANUAL="${ENV_MANUAL}      DATA_DIR=./data                         (Storage Path)\n"
ENV_MANUAL="${ENV_MANUAL}      --------------------------------------------------------"

if [ ! -f "${ENV_FILE}" ]; then
    log_fail ".env file missing in repository root" "${ENV_MANUAL}"
else
    log_pass ".env file exists"

    PERM="$(stat -c "%a" "${ENV_FILE}" 2>/dev/null || stat -f "%A" "${ENV_FILE}" 2>/dev/null || echo "unknown")"
    if [ "${PERM}" = "600" ] || [ "${PERM}" = "400" ]; then
        log_pass ".env file permissions are secure (${PERM})"
    else
        log_warn ".env file permissions are insecure (${PERM})" "Restrict permissions: 'chmod 600 .env'."
    fi

    TOKEN="$(grep -E '^TELEGRAM_BOT_TOKEN=' "${ENV_FILE}" | cut -d '=' -f2- | tr -d ' "\'')"
    USER_IDS="$(grep -E '^ALLOWED_USER_IDS=' "${ENV_FILE}" | cut -d '=' -f2- | tr -d ' "\'')"
    DATA_DIR_CFG="$(grep -E '^DATA_DIR=' "${ENV_FILE}" | cut -d '=' -f2- | tr -d ' "\'')"
    [ -z "${DATA_DIR_CFG}" ] && DATA_DIR_CFG="./data"

    if [ -z "${TOKEN}" ] || [ "${TOKEN}" = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_ExampleToken" ]; then
        log_fail "TELEGRAM_BOT_TOKEN is missing or using default example value" "Open .env and insert your real Telegram Bot API Token from @BotFather."
    elif [[ "${TOKEN}" =~ ^[0-9]{5,12}:[A-Za-z0-9_-]{30,50}$ ]]; then
        log_pass "TELEGRAM_BOT_TOKEN format is valid (${TOKEN:0:10}... [Redacted])"
    else
        log_warn "TELEGRAM_BOT_TOKEN format looks unusual" "Verify your token format obtained from @BotFather."
    fi

    if [ -z "${USER_IDS}" ] || [ "${USER_IDS}" = "123456789,987654321" ]; then
        log_fail "ALLOWED_USER_IDS is missing or using default example values" "Open .env and insert your real numeric Telegram User ID from @userinfobot."
    else
        VALID_USER_IDS="true"
        IFS=',' read -ra ADDR <<< "${USER_IDS}"
        for id_item in "${ADDR[@]}"; do
            clean_id="$(echo "${id_item}" | tr -d ' ')"
            if [[ ! "${clean_id}" =~ ^[0-9]+$ ]]; then
                VALID_USER_IDS="false"
                break
            fi
        done

        if [ "${VALID_USER_IDS}" = "true" ]; then
            log_pass "ALLOWED_USER_IDS configured cleanly (${USER_IDS})"
        else
            log_fail "ALLOWED_USER_IDS contains non-numeric values: '${USER_IDS}'" "ALLOWED_USER_IDS must contain comma-separated numbers only (e.g. 123456789)."
        fi
    fi
fi

# ------------------------------------------------------------------------------
# 6. Data Directory & Registry Check
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}6. Persistent Data Directory & Registry Check${NC}"

RESOLVED_DATA_DIR="${REPO_DIR}/${DATA_DIR_CFG:-data}"
if [ ! -d "${RESOLVED_DATA_DIR}" ]; then
    mkdir -p "${RESOLVED_DATA_DIR}" 2>/dev/null
fi

if [ -d "${RESOLVED_DATA_DIR}" ] && [ -w "${RESOLVED_DATA_DIR}" ]; then
    log_pass "Data directory is writeable: ${RESOLVED_DATA_DIR}"
else
    log_fail "Data directory cannot be created or written: ${RESOLVED_DATA_DIR}" "Check filesystem permissions for ${RESOLVED_DATA_DIR}."
fi

LOCK_FILE="${RESOLVED_DATA_DIR}/.lock"
if [ -f "${LOCK_FILE}" ]; then
    LOCK_PID="$(cat "${LOCK_FILE}" 2>/dev/null || echo "")"
    if [ -n "${LOCK_PID}" ] && kill -0 "${LOCK_PID}" 2>/dev/null; then
        log_warn "Lock file active (PID ${LOCK_PID} is running)" "An instance of AMEVA-WoL appears to be actively running."
    else
        log_info "Lock file exists (Stale PID ${LOCK_PID} or inactive)"
    fi
else
    log_pass "No lock conflict detected"
fi

DEVICES_FILE="${RESOLVED_DATA_DIR}/devices.json"
if [ -f "${DEVICES_FILE}" ]; then
    DEV_COUNT="$(${PYTHON_BIN:-python3} -c "import json; d=json.load(open('${DEVICES_FILE}')); print(len(d))" 2>/dev/null || echo "corrupt")"
    if [ "${DEV_COUNT}" = "corrupt" ]; then
        log_fail "Device registry file (devices.json) contains invalid/corrupt JSON" "Delete or repair ${DEVICES_FILE}."
    else
        log_pass "Device registry (devices.json) exists (${DEV_COUNT} device(s) registered)"
    fi
else
    log_info "Device registry (devices.json) not created yet (Will be created on first /add)"
fi

# ------------------------------------------------------------------------------
# 7. Network Connectivity Check
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}7. Network Connectivity Check${NC}"

if ping -c 1 -W 2 api.telegram.org >/dev/null 2>&1 || ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
    log_pass "Outbound Internet connectivity to Telegram API / DNS: OK"
else
    log_warn "Failed to ping Telegram API / Internet DNS" "Check your Wi-Fi or local network connection on this gateway device."
fi

# ------------------------------------------------------------------------------
# 8. Final Audit Summary & Heuristic Fix Instructions
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}${BLUE}==============================================================${NC}"
echo -e "${BOLD}${BLUE}                  AUDIT SUMMARY REPORT                        ${NC}"
echo -e "${BOLD}${BLUE}==============================================================${NC}"
echo -e "  Passed Checks: ${GREEN}${PASS_COUNT}${NC}"
echo -e "  Warnings:      ${YELLOW}${WARN_COUNT}${NC}"
echo -e "  Failed Checks: ${RED}${FAIL_COUNT}${NC}"
echo ""

if [ ${#HEURISTIC_FIXES[@]} -gt 0 ]; then
    echo -e "${BOLD}${YELLOW}HEURISTIC TROUBLESHOOTING & ACTION REQUIRED:${NC}"
    echo -e "--------------------------------------------------------------"
    for fix in "${HEURISTIC_FIXES[@]}"; do
        echo -e "${fix}"
        echo ""
    done
    echo -e "--------------------------------------------------------------"
fi

if [ "${FAIL_COUNT}" -eq 0 ]; then
    echo -e "${BOLD}${GREEN}SYSTEM STATUS: READY TO RUN${NC}"
    echo -e "Run default mode:   ${CYAN}python -m ameva_wol${NC}"
    echo -e "Run Always-On mode: ${CYAN}python -m ameva_wol --always-on 5${NC}"
    exit 0
else
    echo -e "${BOLD}${RED}SYSTEM STATUS: AUDIT FAILED (${FAIL_COUNT} critical error(s))${NC}"
    echo -e "Please apply the heuristic fixes above before launching AMEVA-WoL."
    exit 1
fi
