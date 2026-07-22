"""Persistent device registry with atomic file writes and async locking."""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from ameva_wol.models import Device
from ameva_wol.security import validate_alias

logger = logging.getLogger("ameva_wol.registry")


class RegistryError(Exception):
    """Base exception for device registry operations."""


class DuplicateAliasError(RegistryError):
    """Raised when adding a device with an alias that already exists without overwrite flag."""


class DeviceNotFoundError(RegistryError):
    """Raised when attempting an operation on a non-existent alias."""


class DeviceRegistry:
    """Thread-safe and async-safe manager for device persistent storage."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.file_path = self.data_dir / "devices.json"
        self._lock = asyncio.Lock()
        self._cache: Optional[Dict[str, Device]] = None

    async def _read_file_unlocked(self) -> Dict[str, Device]:
        """Read and parse devices.json from disk without acquiring lock."""
        if not self.file_path.exists():
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            
            if not isinstance(raw_data, dict):
                logger.error(f"Registry file '{self.file_path}' does not contain a JSON dictionary.")
                return {}

            devices: Dict[str, Device] = {}
            for alias, dev_dict in raw_data.items():
                try:
                    dev = Device.from_dict(dev_dict)
                    devices[dev.alias] = dev
                except Exception as parse_err:
                    logger.warning(f"Skipping malformed device record '{alias}': {parse_err}")
            
            return devices

        except json.JSONDecodeError as err:
            logger.error(f"Corrupt JSON encountered reading device registry '{self.file_path}': {err}")
            raise RegistryError(f"Corrupt device registry file: {err}")
        except Exception as err:
            logger.error(f"Failed to read device registry file '{self.file_path}': {err}")
            raise RegistryError(f"Error reading device registry: {err}")

    async def _write_file_atomic_unlocked(self, devices: Dict[str, Device]) -> None:
        """Write device map to disk atomically using temporary file, flush, fsync, and replace."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self.data_dir / "devices.json.tmp"

        payload = {alias: dev.to_dict() for alias, dev in devices.items()}

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # Set restricted file permissions (600) on POSIX
            if sys.platform != "win32":
                try:
                    os.chmod(tmp_path, 0o600)
                except Exception:
                    pass

            # Atomic replace
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
            logger.error(f"Failed to atomically save device registry to '{self.file_path}': {err}")
            raise RegistryError(f"Atomic registry save failed: {err}")

    async def load(self) -> Dict[str, Device]:
        """Load and cache all registered devices from persistent storage."""
        async with self._lock:
            self._cache = await self._read_file_unlocked()
            return dict(self._cache)

    async def get_all(self) -> Dict[str, Device]:
        """Return all registered devices."""
        async with self._lock:
            if self._cache is None:
                self._cache = await self._read_file_unlocked()
            return dict(self._cache)

    async def get(self, alias: str) -> Optional[Device]:
        """Fetch a registered device by alias (case-insensitive)."""
        norm_alias = validate_alias(alias)
        devices = await self.get_all()
        return devices.get(norm_alias)

    async def add(self, device: Device, overwrite: bool = False) -> Device:
        """Register or update a device in persistent storage.

        Args:
            device: Device model instance to persist.
            overwrite: If False, raises DuplicateAliasError if alias exists.

        Returns:
            Saved Device instance.

        Raises:
            DuplicateAliasError: If alias exists and overwrite is False.
        """
        async with self._lock:
            if self._cache is None:
                self._cache = await self._read_file_unlocked()

            existing = self._cache.get(device.alias)
            if existing is not None and not overwrite:
                raise DuplicateAliasError(
                    f"Device alias '{device.alias}' is already registered. "
                    "Use --overwrite flag to replace existing device."
                )

            # Update cache and save atomically
            self._cache[device.alias] = device
            await self._write_file_atomic_unlocked(self._cache)
            logger.info(f"Registered device '{device.alias}' ({device.mac}, IP: {device.ip or 'N/A'})")
            return device

    async def remove(self, alias: str) -> Device:
        """Remove a registered device by alias.

        Args:
            alias: Target device alias.

        Returns:
            Removed Device object.

        Raises:
            DeviceNotFoundError: If target alias does not exist.
        """
        norm_alias = validate_alias(alias)
        async with self._lock:
            if self._cache is None:
                self._cache = await self._read_file_unlocked()

            if norm_alias not in self._cache:
                raise DeviceNotFoundError(f"No registered device found with alias '{norm_alias}'.")

            removed_dev = self._cache.pop(norm_alias)
            await self._write_file_atomic_unlocked(self._cache)
            logger.info(f"Removed device '{norm_alias}' from registry.")
            return removed_dev
