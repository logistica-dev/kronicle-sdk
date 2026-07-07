from __future__ import annotations

from uuid import UUID

from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase
from kronicle_sdk.models.rbac.kronicle_role import KronicleRole
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

    def model_dump(self, *args, to_payload=True, exclude_none=True, **kwargs) -> dict:
        d = super().model_dump(*args, exclude_none=exclude_none, **kwargs)
        if not to_payload:
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

    def model_dump(self, *args, to_payload=True, exclude_none=True, **kwargs) -> dict:
        d = super().model_dump(*args, to_payload=to_payload, exclude_none=exclude_none, **kwargs)
        if not to_payload:
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
            id=d["id"],
            name=d.get("name"),
            details=d.get("details"),
            description=d.get("description"),
            role=cls._extract_field(d, "role", KronicleRole),
            channel=cls._extract_field(d, "channel", KronicleChannel),
        )

    def model_dump(self, *args, to_payload=True, exclude_none=True, **kwargs) -> dict:
        d = super().model_dump(*args, to_payload=to_payload, exclude_none=exclude_none, **kwargs)
        if not to_payload:
            return d
        d["id"] = uuid_to_str(self.channel.id)
        d["channel_name"] = self.channel.name
        d.pop("channel")
        return d


class KronicleRowAccess(KronicleAccessProfile):
    row_id: UUID

    @classmethod
    def from_json(cls, d) -> KronicleRowAccess:
        return KronicleRowAccess(**d)
