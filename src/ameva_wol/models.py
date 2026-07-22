"""Data models for AMEVA-WoL devices and status representations."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def current_utc_iso() -> str:
    """Return current timestamp in ISO 8601 UTC format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Device:
    """Represents a target computer registered in the Wake-on-LAN gateway.

    Attributes:
        alias: Unique normalized lowercase identifier (1-32 chars, a-z0-9_-).
        mac: Normalized uppercase colon-separated MAC address (e.g. AA:BB:CC:DD:EE:FF).
        ip: Target IPv4 address for reachability ping (Optional).
        broadcast: Broadcast IPv4 address for sending Magic Packet.
        port: Destination UDP port for Magic Packet.
        created_at: ISO 8601 UTC creation timestamp.
        updated_at: ISO 8601 UTC last update timestamp.
    """

    alias: str
    mac: str
    ip: Optional[str]
    broadcast: str
    port: int
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize Device object to dictionary format."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Device":
        """Construct Device object from dictionary with field validation."""
        now = current_utc_iso()
        return cls(
            alias=str(data["alias"]).strip().lower(),
            mac=str(data["mac"]).strip().upper(),
            ip=str(data["ip"]).strip() if data.get("ip") else None,
            broadcast=str(data.get("broadcast", "255.255.255.255")).strip(),
            port=int(data.get("port", 9)),
            created_at=str(data.get("created_at", now)),
            updated_at=str(data.get("updated_at", now)),
        )
