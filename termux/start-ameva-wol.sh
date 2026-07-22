#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# AMEVA-WoL Termux Boot & Startup Script
# ==============================================================================
# Description: Safely boots AMEVA-WoL on Termux (Android), ensuring network
#              availability, holding wake-lock, preventing duplicate instances.
# ==============================================================================

set -euo pipefail

# 1. Determine Repository Directory (resolving symlinks if run from ~/.termux/boot/)
SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || realpath "$0")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

cd "$REPO_DIR"

# 2. Acquire Termux Wake Lock to keep CPU active during device sleep
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
fi

# 3. Wait for Network Connectivity (retry for up to 60 seconds)
MAX_RETRIES=30
RETRY_COUNT=0
echo "AMEVA-WoL Boot: Waiting for network connectivity..."
while ! ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1 && ! ping -c 1 -W 2 1.1.1.1 >/dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
        echo "AMEVA-WoL Boot Warning: Network unreachable after retry timeout. Proceeding anyway."
        break
    fi
    sleep 2
done

# 4. Activate Virtual Environment
if [ -f "$REPO_DIR/.venv/bin/activate" ]; then
    source "$REPO_DIR/.venv/bin/activate"
fi

# 5. Ensure Log & Data Directories Exist
mkdir -p "$REPO_DIR/data" "$REPO_DIR/logs"

# 6. Validate Environment File
if [ ! -f "$REPO_DIR/.env" ]; then
    echo "AMEVA-WoL Boot Error: .env file missing in $REPO_DIR!" >&2
    exit 1
fi

chmod 600 "$REPO_DIR/.env" 2>/dev/null || true

# 7. Start AMEVA-WoL in Always-On mode (exec replaces shell process)
echo "AMEVA-WoL Boot: Launching Always-On mode..."
exec python -m ameva_wol --always-on 5 >> "$REPO_DIR/logs/boot.log" 2>&1
