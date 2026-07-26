"""Tapo P110 Smart Plug integration for AMEVA-WoL."""

import asyncio
import logging
from typing import Dict, Any, Optional

try:
    from plugp100.api.tapo_client import TapoClient
    from plugp100.api.plug_device import PlugDevice
    PLUGP100_AVAILABLE = True
except ImportError as e:
    import traceback
    print(f"\n[!!! CRITICAL ERROR !!!] Failed to import plugp100 at startup: {e}")
    traceback.print_exc()
    TapoClient = None
    PlugDevice = None
    PLUGP100_AVAILABLE = False
    PLUGP100_IMPORT_ERROR = str(e)

logger = logging.getLogger("ameva_wol.tapo_plug")

class TapoManager:
    def __init__(self, tapo_registry: "TapoRegistry"):
        self.tapo_registry = tapo_registry
        
    async def is_configured(self) -> bool:
        cfg = await self.tapo_registry.get_config()
        return bool(cfg.get("email") and cfg.get("password") and cfg.get("devices"))

    async def _get_ip_for_alias(self, alias: Optional[str]) -> str:
        cfg = await self.tapo_registry.get_config()
        devices = cfg.get("devices", {})
        if not devices:
            raise ValueError("No Tapo devices configured.")
        
        if not alias:
            # If no alias provided, and there's only 1 device, use it.
            if len(devices) == 1:
                return next(iter(devices.values()))["ip"]
            else:
                raise ValueError(f"Multiple devices configured. Please specify an alias: {', '.join(devices.keys())}")
        
        alias = alias.lower()
        if alias not in devices:
            raise ValueError(f"Device alias '{alias}' not found in Tapo Registry.")
        
        return devices[alias]["ip"]

    async def _get_plug(self, alias: Optional[str]) -> "PlugDevice":
        ip = await self._get_ip_for_alias(alias)
        cfg = await self.tapo_registry.get_config()
        if not TapoClient:
            print(f"\n[DEBUG] _get_plug called, but PLUGP100 is not available. Error was: {PLUGP100_IMPORT_ERROR}")
            raise ImportError(f"plugp100 library is not installed. Error: {PLUGP100_IMPORT_ERROR}")
        
        from plugp100.common.credentials import AuthCredential
        cred = AuthCredential(cfg["email"], cfg["password"])
        client = TapoClient(cred, ip)
        await client.initialize()
        plug = PlugDevice(client)
        return plug

    async def turn_on(self, alias: Optional[str] = None) -> str:
        plug = await self._get_plug(alias)
        res = await plug.on()
        if res.is_ok:
            return "✅ Successfully turned ON"
        return f"❌ Failed to turn on: {res.error_message}"

    async def turn_off(self, alias: Optional[str] = None) -> str:
        plug = await self._get_plug(alias)
        res = await plug.off()
        if res.is_ok:
            return "✅ Successfully turned OFF"
        return f"❌ Failed to turn off: {res.error_message}"

    async def reboot(self, alias: Optional[str] = None, delay_seconds: int = 10) -> str:
        plug = await self._get_plug(alias)
        res_off = await plug.off()
        if not res_off.is_ok:
            return f"❌ Failed to turn off during reboot: {res_off.error_message}"
        
        await asyncio.sleep(delay_seconds)
        
        res_on = await plug.on()
        if res_on.is_ok:
            return f"✅ Successfully rebooted (Off -> {delay_seconds}s -> On)"
        return f"⚠️ Turned off, but failed to turn back on: {res_on.error_message}"

    async def get_status(self, alias: Optional[str] = None) -> str:
        plug = await self._get_plug(alias)
        info_res = await plug.get_state()
        energy_res = await plug.get_energy_usage()

        if not info_res.is_ok:
            return f"❌ Failed to get device state: {info_res.error_message}"
        
        state_obj = info_res.value
        state = "🟢 ON" if getattr(state_obj, "device_on", False) else "🔴 OFF"
        
        lines = [f"📊 Tapo Plug Status", f"• State: {state}"]
        
        if energy_res.is_ok:
            energy = energy_res.value
            lines.append(f"• Current Power: `{energy.current_power} W`")
            lines.append(f"• Today's Energy: `{energy.today_energy / 1000:.2f} kWh`")
            lines.append(f"• Month's Energy: `{energy.month_energy / 1000:.2f} kWh`")
            lines.append(f"• Today's Runtime: `{energy.today_runtime} minutes`")
            lines.append(f"• Month's Runtime: `{energy.month_runtime} minutes`")
        
        return "\n".join(lines)
