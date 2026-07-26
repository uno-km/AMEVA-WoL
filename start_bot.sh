#!/bin/bash

# ==========================================
# AMEVA-WoL Termux All-in-One Auto-Runner
# ==========================================

# 1. Acquire Android Wake Lock (Prevents CPU sleep when screen is off)
echo "[*] Acquiring Termux Wake Lock..."
termux-wake-lock

# 1.5 Auto-Update (Git Pull)
echo "[*] Updating to the latest code..."
git reset --hard
git pull


# 2. Install native dependencies (Bypass pip compilation errors on Android)
# (py3compile 에러가 떠도 무시하고 진행됩니다. 실제 설치는 정상적으로 되기 때문입니다.)
echo "[*] Ensuring native Android packages are installed..."
pkg install -y python-cryptography python-psutil || true

# 3. Install remaining python dependencies
echo "[*] Installing Python requirements..."
pip install -r requirements.txt
echo "[*] Force reinstalling plugp100 as requested..."
pip install --upgrade --force-reinstall plugp100

# 파이썬이 src 안의 모듈을 찾을 수 있도록 환경변수 추가
export PYTHONPATH="src:$PYTHONPATH"

# 4. Infinite Restart Loop
echo "[*] Starting AMEVA-WoL Daemon..."
while true; do
    echo "----------------------------------------"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Starting Python Bot..."
    echo "----------------------------------------"
    
    python -m ameva_wol
    
    # If it reaches here, the bot crashed or was killed
    echo "[!] WARNING: Bot has stopped or crashed!"
    echo "[!] Restarting in 5 seconds... (Press Ctrl+C quickly to stop completely)"
    
    # Wait 5 seconds before restarting
    sleep 5
done
