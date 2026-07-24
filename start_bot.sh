#!/bin/bash

# ==========================================
# AMEVA-WoL Extreme Auto-Restart Script
# ==========================================

# 1. Acquire Android Wake Lock (Prevents CPU sleep when screen is off)
echo "[*] Acquiring Termux Wake Lock..."
termux-wake-lock

# 2. Check and activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "[*] Activating virtual environment..."
    source venv/bin/activate
fi

# Move into src directory if we are at project root, so python finds the module
if [ -d "src" ]; then
    cd src
fi

# 3. Infinite Restart Loop
echo "[*] Starting AMEVA-WoL Daemon..."
while true; do
    echo "----------------------------------------"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting Python Bot..."
    echo "----------------------------------------"
    
    python -m ameva_wol

    
    # If it reaches here, the bot crashed or was killed
    echo "[!] WARNING: Bot has stopped or crashed!"
    echo "[!] Restarting in 5 seconds... (Press Ctrl+C quickly to stop completely)"
    
    # Wait 5 seconds before restarting to prevent rapid crash loops (CPU spam)
    sleep 5
done
