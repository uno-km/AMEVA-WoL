"""Persistent registry for Tapo power devices and credentials."""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Any

from ameva_wol.security import validate_alias

logger = logging.getLogger("ameva_wol.tapo_registry")

class TapoRegistryError(Exception):
    """Base exception for tapo registry operations."""

class TapoRegistry:
    """Thread-safe and async-safe manager for Tapo power device persistent storage."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.file_path = self.data_dir / "power_devices.json"
        self._lock = asyncio.Lock()
        self._cache: Optional[Dict[str, Any]] = None

    async def _read_file_unlocked(self) -> Dict[str, Any]:
        """Read and parse power_devices.json from disk."""
        if not self.file_path.exists():
            return {"email": None, "password": None, "devices": {}}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            
            if not isinstance(raw_data, dict):
                logger.error(f"Tapo registry file '{self.file_path}' is not a dict.")
                return {"email": None, "password": None, "devices": {}}
                
            if "devices" not in raw_data:
                raw_data["devices"] = {}

            return raw_data

        except json.JSONDecodeError as err:
            logger.error(f"Corrupt JSON encountered reading '{self.file_path}': {err}")
            return {"email": None, "password": None, "devices": {}}
        except Exception as err:
            logger.error(f"Failed to read device registry file '{self.file_path}': {err}")
            return {"email": None, "password": None, "devices": {}}

    async def _write_file_atomic_unlocked(self, data: Dict[str, Any]) -> None:
        """Write to disk atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self.data_dir / "power_devices.json.tmp"

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            if sys.platform != "win32":
                try:
                    os.chmod(tmp_path, 0o600)
                except Exception:
                    pass

            os.replace(tmp_path, self.file_path)

            if sys.platform != "win32" and self.file_path.exists():
                try:
                    os.chmod(self.file_path, 0o600)
                except Exception:
                    pass

        except Exception as err:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            logger.error(f"Failed to save tapo registry to '{self.file_path}': {err}")
            raise TapoRegistryError(f"Atomic save failed: {err}")

    async def get_config(self) -> Dict[str, Any]:
        """Get the full Tapo configuration including email, password, and devices."""
        async with self._lock:
            if self._cache is None:
                self._cache = await self._read_file_unlocked()
            return dict(self._cache)
            
    async def get_device_ip(self, alias: str) -> Optional[str]:
        cfg = await self.get_config()
        devices = cfg.get("devices", {})
        dev = devices.get(alias)
        return dev.get("ip") if dev else None

    async def add_device(self, alias: str, email: str, password: str, ip: str, mac: str) -> None:
        """Register Tapo device and credentials in persistent storage."""
        norm_alias = validate_alias(alias)
        async with self._lock:
            if self._cache is None:
                self._cache = await self._read_file_unlocked()

            self._cache["email"] = email
            self._cache["password"] = password
            
            if "devices" not in self._cache:
                self._cache["devices"] = {}
                
            self._cache["devices"][norm_alias] = {
                "alias": norm_alias,
                "ip": ip,
                "mac": mac
            }
            
            await self._write_file_atomic_unlocked(self._cache)
            logger.info(f"Registered Tapo device '{norm_alias}' (IP: {ip})")
