# kronicle_sdk/models/rbac/kronicle_policy.py
from __future__ import annotations

from uuid import UUID

from kronicle_sdk.models.iso_datetime import IsoDateTime
from kronicle_sdk.models.rbac.kronicle_access_profile import (
    KronicleChannelAccess,
    KronicleRowAccess,
    KronicleZoneAccess,
)
from kronicle_sdk.models.rbac.kronicle_group import KronicleGroup
from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase
from kronicle_sdk.models.rbac.kronicle_user import KronicleUser
from kronicle_sdk.utils.str_utils import uuid_to_str


class KronicleSubject(KronicleRbacBase):
    user_id: UUID | None = None
    group_id: UUID | None = None

    @classmethod
    def from_user(cls, user: KronicleUser):
        return KronicleSubject(name=user.name, user_id=user.id)

    @classmethod
    def from_group(cls, group: KronicleGroup):
        return KronicleSubject(name=group.name, group_id=group.id)


class KroniclePolicy(KronicleRbacBase):
    subject: KronicleSubject
    is_delegation: bool = False
    delegation_start: IsoDateTime | None = None
    delegation_end: IsoDateTime | None = None

    @classmethod
    def _extract_self(cls, d: dict) -> dict:
        return {
            "id": d["id"],
            "name": d.get("name"),
            "details": d.get("details"),
            "description": d.get("description"),
            "is_delegation": d.get("is_delegation"),
            "delegation_start": d.get("delegation_start"),
            "delegation_end": d.get("delegation_end"),
            "subject": cls._extract_field(d, "subject", KronicleSubject),
        }


class KronicleZonePolicy(KroniclePolicy):
    access_profile: KronicleZoneAccess  # type: ignore

    @classmethod
    def from_json(cls, d) -> KronicleZonePolicy:
        return KronicleZonePolicy(
            **cls._extract_self(d),
            access_profile=cls._extract_field(d, "access", KronicleZoneAccess),
        )

    def model_dump(self) -> dict:
        d = super().model_dump()
        d["zone_id"] = uuid_to_str(self.access_profile.zone.id)
        d.pop("access_profile")
        return d


class KronicleChannelPolicy(KroniclePolicy):
    access_profile: KronicleChannelAccess

    @classmethod
    def from_json(cls, d) -> KronicleChannelPolicy:
        return KronicleChannelPolicy(
            **cls._extract_self(d),
            access_profile=cls._extract_field(d, "access", KronicleChannelAccess),
        )

    def model_dump(self) -> dict:
        d = super().model_dump()
        d["id"] = uuid_to_str(self.access_profile.channel.id)
        d.pop("access_profile")
        return d


class KronicleRowPolicy(KroniclePolicy):
    access_profile: KronicleRowAccess

    def model_dump(self) -> dict:
        d = super().model_dump()
        d["row_id"] = uuid_to_str(self.access_profile.row_id)
        d.pop("access_profile")
        return d
