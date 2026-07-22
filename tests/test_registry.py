"""Unit tests for persistent device registry, atomic storage, and concurrency."""

import json
from pathlib import Path
import pytest

from ameva_wol.models import Device, current_utc_iso
from ameva_wol.registry import (
    DeviceNotFoundError,
    DuplicateAliasError,
    DeviceRegistry,
    RegistryError,
)


@pytest.mark.asyncio
async def test_registry_add_get_remove(tmp_path: Path) -> None:
    """Test standard add, retrieve, and remove operations."""
    registry = DeviceRegistry(tmp_path)
    
    dev = Device(
        alias="server",
        mac="AA:BB:CC:DD:EE:01",
        ip="192.168.0.50",
        broadcast="192.168.0.255",
        port=9,
        created_at=current_utc_iso(),
        updated_at=current_utc_iso(),
    )

    # 1. Add device
    await registry.add(dev)
    retrieved = await registry.get("server")
    assert retrieved is not None
    assert retrieved.mac == "AA:BB:CC:DD:EE:01"
    assert retrieved.ip == "192.168.0.50"

    # 2. Get all
    all_devs = await registry.get_all()
    assert "server" in all_devs

    # 3. Remove device
    removed = await registry.remove("server")
    assert removed.alias == "server"
    assert await registry.get("server") is None


@pytest.mark.asyncio
async def test_registry_duplicate_rejection_and_overwrite(tmp_path: Path) -> None:
    """Test duplicate alias rejection and explicit --overwrite support."""
    registry = DeviceRegistry(tmp_path)
    
    dev1 = Device("nas", "AA:BB:CC:DD:EE:01", "192.168.0.10", "192.168.0.255", 9, current_utc_iso(), current_utc_iso())
    dev2 = Device("nas", "AA:BB:CC:DD:EE:99", "192.168.0.99", "192.168.0.255", 9, current_utc_iso(), current_utc_iso())

    await registry.add(dev1)

    # Duplicate without overwrite raises error
    with pytest.raises(DuplicateAliasError):
        await registry.add(dev2, overwrite=False)

    # Duplicate with overwrite replaces existing record
    await registry.add(dev2, overwrite=True)
    updated = await registry.get("nas")
    assert updated is not None
    assert updated.mac == "AA:BB:CC:DD:EE:99"
    assert updated.ip == "192.168.0.99"


@pytest.mark.asyncio
async def test_registry_atomic_file_creation(tmp_path: Path) -> None:
    """Test atomic creation of devices.json file."""
    registry = DeviceRegistry(tmp_path)
    dev = Device("workstation", "11:22:33:44:55:66", "192.168.0.20", "192.168.0.255", 9, current_utc_iso(), current_utc_iso())

    await registry.add(dev)

    json_file = tmp_path / "devices.json"
    assert json_file.exists()

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "workstation" in data
    assert data["workstation"]["mac"] == "11:22:33:44:55:66"


@pytest.mark.asyncio
async def test_registry_corrupt_file_handling(tmp_path: Path) -> None:
    """Test handling of corrupt JSON in devices.json."""
    json_file = tmp_path / "devices.json"
    json_file.write_text("{ corrupt json data ... ", encoding="utf-8")

    registry = DeviceRegistry(tmp_path)
    with pytest.raises(RegistryError, match="Corrupt device registry"):
        await registry.load()


@pytest.mark.asyncio
async def test_registry_remove_nonexistent_raises(tmp_path: Path) -> None:
    """Test removing a non-existent alias raises DeviceNotFoundError."""
    registry = DeviceRegistry(tmp_path)
    with pytest.raises(DeviceNotFoundError):
        await registry.remove("non_existent_alias")
