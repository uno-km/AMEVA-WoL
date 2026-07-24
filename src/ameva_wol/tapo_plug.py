"""Tapo P110 Smart Plug integration for AMEVA-WoL."""

import asyncio
import logging
from typing import Dict, Any, Optional

try:
    from plugp100.api.tapo_client import TapoClient
    from plugp100.api.plug_device import PlugDevice
except ImportError:
    TapoClient = None
    PlugDevice = None

logger = logging.getLogger("ameva_wol.tapo_plug")

class TapoManager:
    def __init__(self, email: Optional[str], password: Optional[str], devices: Dict[str, str]):
        self.email = email
        self.password = password
        self.devices = devices  # {alias: ip}
        self.client = None
        
        if self.email and self.password and TapoClient:
            self.client = TapoClient(self.email, self.password)

    def is_configured(self) -> bool:
        return bool(self.client and self.devices)

    def _get_ip_for_alias(self, alias: Optional[str]) -> str:
        if not self.devices:
            raise ValueError("No Tapo devices configured.")
        
        if not alias:
            # If no alias provided, and there's only 1 device, use it.
            if len(self.devices) == 1:
                return next(iter(self.devices.values()))
            else:
                raise ValueError(f"Multiple devices configured. Please specify an alias: {', '.join(self.devices.keys())}")
        
        alias = alias.lower()
        if alias not in self.devices:
            raise ValueError(f"Device alias '{alias}' not found in TAPO_DEVICES.")
        
        return self.devices[alias]

    async def _get_plug(self, alias: Optional[str]) -> "PlugDevice":
        ip = self._get_ip_for_alias(alias)
        plug = PlugDevice(self.client, ip)
        await plug.login()
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
        info_res = await plug.get_device_info()
        energy_res = await plug.get_energy_usage()

        if not info_res.is_ok:
            return f"❌ Failed to get device info: {info_res.error_message}"
        
        info = info_res.value
        state = "🟢 ON" if info.device_on else "🔴 OFF"
        
        lines = [f"📊 Tapo Plug Status", f"• State: {state}"]
        
        if energy_res.is_ok:
            energy = energy_res.value
            current_power = energy.current_power
            lines.append(f"• Current Power: `{current_power} W`")
        
        return "\n".join(lines)
