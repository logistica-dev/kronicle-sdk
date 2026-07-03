from __future__ import annotations

from kronicle_sdk.models.iso_datetime import IsoDateTime
from kronicle_sdk.models.rbac.kronicle_access_profile import (
    KronicleAccessProfile,
    KronicleChannelAccess,
    KronicleRowAccess,
    KronicleZoneAccess,
)
from kronicle_sdk.models.rbac.kronicle_group import KronicleGroup
from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase
from kronicle_sdk.models.rbac.kronicle_user import KronicleUser
from kronicle_sdk.utils.str_utils import uuid_to_str


class KroniclePolicy(KronicleRbacBase):
    access_profile: KronicleAccessProfile
    subject: KronicleUser | KronicleGroup
    is_delegation: bool = False
    delegation_start: IsoDateTime | None = None
    delegation_end: IsoDateTime | None = None

    def model_dump(self) -> dict:
        d = super().model_dump()
        d["subject_id"] = uuid_to_str(self.subject.id)
        d["access_profile"] = uuid_to_str(self.access_profile.id)
        d.pop("subject")
        d.pop("access_profile")
        return d


class KronicleZonePolicy(KroniclePolicy):
    access_profile: KronicleZoneAccess
    pass


class KronicleChannelPolicy(KroniclePolicy):
    access_profile: KronicleChannelAccess
    pass


class KronicleRowPolicy(KroniclePolicy):
    access_profile: KronicleRowAccess
    pass
