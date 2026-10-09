# kronicle_sdk/models/rbac/kronicle_policy.py
from __future__ import annotations

from typing import Literal
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
from kronicle_sdk.utils.str_utils import serialize_uuid


class KronicleSubject(KronicleRbacBase):
    type: Literal["user", "group"]
    user_id: UUID | None = None
    group_id: UUID | None = None

    @classmethod
    def from_user(cls, user: KronicleUser):
        return KronicleSubject(name=user.name, user_id=user.id, type="user")

    @classmethod
    def from_group(cls, group: KronicleGroup):
        return KronicleSubject(name=group.name, group_id=group.id, type="group")


class KroniclePolicy(KronicleRbacBase):
    subject: KronicleSubject
    is_delegation: bool = False
    delegation_start: IsoDateTime | None = None
    delegation_end: IsoDateTime | None = None

    @classmethod
    def _extract_self(cls, d: dict) -> dict:
        return {
            "id": d.get("id"),
            "name": d.get("name"),
            "details": d.get("details"),
            "description": d.get("description"),
            "is_delegation": d.get("is_delegation"),
            "delegation_start": d.get("delegation_start"),
            "delegation_end": d.get("delegation_end"),
            "subject": cls._extract_field(d, "subject", KronicleSubject),
        }

    @staticmethod
    def _same_id(a: object, b: object) -> bool:
        """True only when both ids are present and equal (``None`` never matches)."""
        return a is not None and a == b

    def _matches_subject(self, other: KroniclePolicy) -> bool:
        return self.subject.type == other.subject.type and self._same_id(
            self.subject.group_id or self.subject.user_id,
            other.subject.group_id or other.subject.user_id,
        )


class KronicleZonePolicy(KroniclePolicy):
    access_profile: KronicleZoneAccess  # type: ignore

    @classmethod
    def from_json(cls, d) -> KronicleZonePolicy:
        return KronicleZonePolicy(
            **cls._extract_self(d),
            access_profile=cls._extract_field(d, "access_profile", KronicleZoneAccess),
        )

    def matches(self, other: KronicleZonePolicy) -> bool:
        return (
            self._matches_subject(other)
            and self._same_id(self.access_profile.role.id, other.access_profile.role.id)
            and self._same_id(self.access_profile.zone.id, other.access_profile.zone.id)
        )

    def flatten(self) -> dict:
        d = self.model_dump()
        d["zone_id"] = serialize_uuid(self.access_profile.zone.ensure_has_id())
        d.pop("access_profile")
        return d


class KronicleChannelPolicy(KroniclePolicy):
    access_profile: KronicleChannelAccess

    @classmethod
    def from_json(cls, d) -> KronicleChannelPolicy:
        return KronicleChannelPolicy(
            **cls._extract_self(d),
            access_profile=cls._extract_field(d, "access_profile", KronicleChannelAccess),
        )

    def matches(self, other: KronicleChannelPolicy) -> bool:
        return (
            self._matches_subject(other)
            and self._same_id(self.access_profile.role.id, other.access_profile.role.id)
            and self._same_id(self.access_profile.channel.id, other.access_profile.channel.id)
        )

    def flatten(self) -> dict:
        d = self.model_dump()
        d["channel_id"] = serialize_uuid(self.access_profile.channel.ensure_has_id())
        d.pop("access_profile")
        return d


class KronicleRowPolicy(KroniclePolicy):
    access_profile: KronicleRowAccess

    @classmethod
    def from_json(cls, d) -> KronicleRowPolicy:
        return KronicleRowPolicy(
            **cls._extract_self(d),
            access_profile=cls._extract_field(d, "access_profile", KronicleRowAccess),
        )

    def matches(self, other: KronicleRowPolicy) -> bool:
        return (
            self._matches_subject(other)
            and self._same_id(self.access_profile.role.id, other.access_profile.role.id)
            and self._same_id(self.access_profile.row.id, other.access_profile.row.id)
        )

    def flatten(self) -> dict:
        d = self.model_dump()
        d["row_id"] = serialize_uuid(self.access_profile.row.id)
        d.pop("access_profile")
        return d
