from __future__ import annotations

from uuid import UUID

from kronicle_sdk.models.data.kronicle_payload import KroniclePayload
from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase
from kronicle_sdk.models.rbac.kronicle_role import KronicleRole
from kronicle_sdk.models.rbac.kronicle_zone import KronicleZone
from kronicle_sdk.utils.str_utils import uuid_to_str


class KronicleAccessProfile(KronicleRbacBase):
    role: KronicleRole
    description: str | None = None

    @classmethod
    def from_json(d: dict) -> KronicleAccessProfile:
        if d.get("zone_id"):
            return KronicleZoneAccess(**d)
        if d.get("channel_id"):
            return KronicleChannelAccess(**d)
        return KronicleRowAccess(**d)

    def model_dump(self) -> dict:
        d = super().model_dump()
        d["role_id"] = uuid_to_str(self.role.id)
        d["role_name"] = self.role.name
        d.pop("role")
        return d


class KronicleZoneAccess(KronicleAccessProfile):
    zone: KronicleZone

    def model_dump(self) -> dict:
        d = super().model_dump()
        d["zone_id"] = uuid_to_str(self.zone.id)
        d["zone_name"] = self.zone.name
        d.pop("zone")
        return d


class KronicleChannelAccess(KronicleAccessProfile):
    channel: KroniclePayload

    def model_dump(self) -> dict:
        d = super().model_dump()
        d["channel_id"] = uuid_to_str(self.channel.channel_id)
        d["channel_name"] = self.channel.name
        d.pop("channel")
        return d


class KronicleRowAccess(KronicleAccessProfile):
    row_id: UUID
