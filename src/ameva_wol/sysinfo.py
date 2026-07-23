import asyncio
import json
import logging
import platform
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional

import httpx
import psutil
import speedtest

logger = logging.getLogger("ameva_wol.sysinfo")

def run_cmd(cmd: list[str], timeout: int = 5) -> str:
    """Run a shell command and return stdout as string."""
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return ""

async def run_cmd_async(cmd: list[str], timeout: int = 5) -> str:
    """Run a shell command asynchronously."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode().strip()
    except Exception:
        return ""

async def get_battery_info() -> str:
    """Get battery info from Termux or fallback to psutil."""
    termux_batt = await run_cmd_async(["termux-battery-status"], timeout=3)
    if termux_batt:
        try:
            data = json.loads(termux_batt)
            return f"{data.get('percentage', '?')}% ({data.get('status', 'UNKNOWN')}), Temp: {data.get('temperature', '?')}°C, Health: {data.get('health', '?')}"
        except json.JSONDecodeError:
            pass
    
    # Fallback to psutil
    batt = psutil.sensors_battery()
    if batt:
        plugged = "Plugged In" if batt.power_plugged else "Discharging"
        return f"{batt.percent}% ({plugged})"
    return "N/A"

async def get_location() -> str:
    """Get location via Termux GPS or IP fallback."""
    # Try termux-location (network provider usually faster than gps)
    termux_loc = await run_cmd_async(["termux-location", "-p", "network"], timeout=5)
    if termux_loc:
        try:
            data = json.loads(termux_loc)
            lat = data.get("latitude")
            lon = data.get("longitude")
            if lat and lon:
                return f"GPS: {lat}, {lon} (Acc: {data.get('accuracy', '?')}m)"
        except Exception:
            pass

    # Fallback to IP API
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://ip-api.com/json/")
            data = resp.json()
            if data.get("status") == "success":
                return f"IP: {data.get('country')}, {data.get('city')} (ISP: {data.get('isp')})"
    except Exception:
        pass
    
    return "N/A"

async def get_sensors_info() -> str:
    """Get sensor data from termux-sensor."""
    # Get 1 reading from all sensors
    out = await run_cmd_async(["termux-sensor", "-s", "", "-n", "1"], timeout=3)
    if not out:
        return "N/A"
    try:
        data = json.loads(out)
        sensors_summary = []
        # Look for gyro, accel, light
        for sensor_name, sensor_data in data.items():
            name_lower = sensor_name.lower()
            if "gyro" in name_lower:
                vals = sensor_data.get("values", [])
                sensors_summary.append(f"Gyro: {vals}")
            elif "accel" in name_lower:
                vals = sensor_data.get("values", [])
                sensors_summary.append(f"Accel: {vals}")
            elif "light" in name_lower:
                vals = sensor_data.get("values", [])
                sensors_summary.append(f"Light: {vals[0] if vals else '?'} lx")
        if sensors_summary:
            return ", ".join(sensors_summary)
        return "Sensors detected, but no standard values parsed."
    except Exception:
        return "Data format error"

async def get_android_props() -> str:
    """Extract interesting Android props (screen, touch, etc.)."""
    if platform.system() != "Linux" or not hasattr(platform, "android_ver"):
        # Just simple heuristics, Termux runs on Linux kernel
        pass
    
    props = await run_cmd_async(["getprop"], timeout=2)
    if not props:
        return "N/A"
    
    interesting = {}
    for line in props.splitlines():
        if "ro.product.model" in line: interesting["Model"] = line.split("]: [")[-1].strip("]")
        if "ro.board.platform" in line: interesting["Platform"] = line.split("]: [")[-1].strip("]")
        if "ro.sf.lcd_density" in line: interesting["LCD Density"] = line.split("]: [")[-1].strip("]")
        if "persist.sys.touch.points" in line: interesting["Touch Points"] = line.split("]: [")[-1].strip("]")
    
    if interesting:
        return ", ".join(f"{k}: {v}" for k, v in interesting.items())
    return "Props inaccessible"

def run_speedtest_sync() -> str:
    """Run speedtest-cli synchronously."""
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        dl = st.download() / 1_000_000  # Mbps
        ul = st.upload() / 1_000_000    # Mbps
        ping = st.results.ping
        return f"⬇️ {dl:.2f} Mbps | ⬆️ {ul:.2f} Mbps | 🏓 {ping} ms"
    except Exception as e:
        return f"Error: {str(e)}"

async def collect_sysinfo(include_speedtest: bool = False) -> str:
    """Collects all system information."""
    
    # 1. OS & CPU & RAM
    uname = platform.uname()
    os_info = f"{uname.system} {uname.release} ({uname.machine})"
    
    cpu_usage = psutil.cpu_percent(interval=0.5)
    cpu_cores = psutil.cpu_count(logical=True)
    
    mem = psutil.virtual_memory()
    mem_total = mem.total / (1024**3)
    mem_used = mem.used / (1024**3)
    
    disk = psutil.disk_usage('/')
    disk_total = disk.total / (1024**3)
    disk_used = disk.used / (1024**3)

    # 2. Advanced / Termux Info
    batt, loc, sensors, props = await asyncio.gather(
        get_battery_info(),
        get_location(),
        get_sensors_info(),
        get_android_props()
    )

    report = [
        f"📱 **Host System Information**",
        f"• **OS:** `{os_info}`",
        f"• **Hardware:** `{props}`",
        f"• **CPU:** `{cpu_usage}% ({cpu_cores} Cores)`",
        f"• **RAM:** `{mem_used:.1f}GB / {mem_total:.1f}GB ({mem.percent}%)`",
        f"• **Storage:** `{disk_used:.1f}GB / {disk_total:.1f}GB ({disk.percent}%)`",
        f"• **Battery:** `{batt}`",
        f"• **Location:** `{loc}`",
        f"• **Sensors:** `{sensors}`",
    ]

    if include_speedtest:
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            speed = await loop.run_in_executor(pool, run_speedtest_sync)
        report.append(f"• **Network Speed:** `{speed}`")
    else:
        report.append(f"• **Network Speed:** `⏳ Measuring...`")

    return "\n".join(report)
