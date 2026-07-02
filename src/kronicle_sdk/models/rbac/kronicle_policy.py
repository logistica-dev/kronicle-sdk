from __future__ import annotations

from uuid import UUID

from kronicle_sdk.models.iso_datetime import IsoDateTime
from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase


class KroniclePolicy(KronicleRbacBase):
    access_profile_id: UUID
    subject_id: UUID
    is_delegation: bool = False
    delegation_start: IsoDateTime | None = None
    delegation_end: IsoDateTime | None = None


class KronicleZonePolicy(KroniclePolicy):
    pass


class KronicleChannelPolicy(KroniclePolicy):
    pass


class KronicleRowPolicy(KroniclePolicy):
    pass
