from __future__ import annotations

from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase
from kronicle_sdk.models.rbac.kronicle_role import KronicleRole
from kronicle_sdk.models.rbac.kronicle_row import KronicleRow
from kronicle_sdk.models.rbac.kronicle_zone import KronicleZone
from kronicle_sdk.utils.str_utils import uuid_to_str


class KronicleAccessProfile(KronicleRbacBase):
    role: KronicleRole
    description: str | None = None

    @classmethod
    def _extract_self(cls, d: dict) -> dict:
        return {
            "id": d["id"],
            "name": d.get("name"),
            "details": d.get("details"),
            "description": d.get("description"),
            "role": cls._extract_field(d, "role", KronicleRole),
        }

    def model_dump(self, *args, mode="json", flatten=False, exclude_none=True, **kwargs) -> dict:
        d = super().model_dump(*args, mode=mode, exclude_none=exclude_none, **kwargs)
        if not flatten:
            return d
        d["role_id"] = uuid_to_str(self.role.id)
        d["role_name"] = self.role.name
        d.pop("role")
        return d


class KronicleZoneAccess(KronicleAccessProfile):
    zone: KronicleZone

    @classmethod
    def from_json(cls, d) -> KronicleZoneAccess:
        return KronicleZoneAccess(
            **cls._extract_self(d),
            zone=cls._extract_field(d, "zone", KronicleZone),
        )

    def model_dump(self, *args, mode="json", flatten=False, exclude_none=True, **kwargs) -> dict:
        d = super().model_dump(*args, mode=mode, flatten=flatten, exclude_none=exclude_none, **kwargs)
        if not flatten:
            return d
        d["zone_id"] = uuid_to_str(self.zone.id)
        d["zone_name"] = self.zone.name
        d.pop("zone")
        return d


class KronicleChannelAccess(KronicleAccessProfile):
    channel: KronicleChannel

    @classmethod
    def from_json(cls, d) -> KronicleChannelAccess:
        return KronicleChannelAccess(
            **cls._extract_self(d),
            channel=cls._extract_field(d, "channel", KronicleChannel),
        )

    def model_dump(self, *args, mode="json", flatten=False, exclude_none=True, **kwargs) -> dict:
        d = super().model_dump(*args, mode=mode, flatten=flatten, exclude_none=exclude_none, **kwargs)
        if not flatten:
            return d
        d["channel_id"] = uuid_to_str(self.channel.id)
        d["channel_name"] = self.channel.name
        d.pop("channel")
        return d


class KronicleRowAccess(KronicleAccessProfile):
    row: KronicleRow

    @classmethod
    def from_json(cls, d) -> KronicleRowAccess:
        return KronicleRowAccess(
            **cls._extract_self(d),
            row=cls._extract_field(d, "row", KronicleRow),
        )


if __name__ == "__main__":  # pragma: no cover
    zone_access = KronicleZoneAccess.from_json(
        {
            "id": "c64c79e1-941c-45d4-a333-5151f2efc098",
            "name": "Zone ZoneA Writer access",
            "details": None,
            "role": {
                "id": "d0332ec8-78ba-476c-99b5-cfc0af17fda7",
                "name": "Writer",
                "details": {},
                "description": "",
                "permissions": ["data:access", "channel:read", "row:create"],
                "restrictions": [],
            },
            "description": "Write access to Zone A",
            "zone": {"id": "e1e90f77-5e14-4a1d-a2f8-2a5a420e6c1e", "name": "ZoneA", "details": {"init": True}},
        }
    )

    print(zone_access)
