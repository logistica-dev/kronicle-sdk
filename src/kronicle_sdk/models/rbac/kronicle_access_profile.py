from __future__ import annotations

from uuid import UUID

from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase


class KronicleAccessProfile(KronicleRbacBase):
    role_id: UUID
    description: str | None = None


class KronicleZoneAccess(KronicleAccessProfile):
    zone_id: UUID


class KronicleChannelAccess(KronicleAccessProfile):
    channel_id: UUID


class KronicleRowAccessProfile(KronicleAccessProfile):
    row_id: UUID
