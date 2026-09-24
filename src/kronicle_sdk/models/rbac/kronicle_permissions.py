from __future__ import annotations

from kronicle_sdk.models.rbac.kronicle_group import KronicleGroup
from kronicle_sdk.models.rbac.kronicle_policy import (
    KronicleChannelPolicy,
    KronicleRowPolicy,
    KronicleZonePolicy,
)
from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase
from kronicle_sdk.models.rbac.kronicle_role import KronicleRole
from pydantic import BaseModel, Field


class KronicleGroupRole(BaseModel):
    group: KronicleGroup
    role: KronicleRole

    @classmethod
    def from_json(cls, d: dict) -> KronicleGroupRole:
        return KronicleGroupRole(
            group=KronicleRbacBase._extract_field(d, "group", KronicleGroup),
            role=KronicleRbacBase._extract_field(d, "role", KronicleRole),
        )


class KroniclePermissions(KronicleRbacBase):
    direct_roles: list[KronicleRole] = Field(default_factory=list)
    group_roles: list[KronicleGroupRole] = Field(default_factory=list)
    zone_policies: list[KronicleZonePolicy] = Field(default_factory=list)
    channel_policies: list[KronicleChannelPolicy] = Field(default_factory=list)
    row_policies: list[KronicleRowPolicy] = Field(default_factory=list)

    @classmethod
    def from_json(cls, d: dict) -> KroniclePermissions:
        return KroniclePermissions(
            direct_roles=[KronicleRole.from_json(r.get("role") or r) for r in d.get("direct_roles", [])],
            group_roles=[KronicleGroupRole.from_json(gr) for gr in d.get("group_roles", [])],
            zone_policies=[KronicleZonePolicy.from_json(p) for p in d.get("zone_policies", [])],
            channel_policies=[KronicleChannelPolicy.from_json(p) for p in d.get("channel_policies", [])],
            row_policies=[KronicleRowPolicy.from_json(p) for p in d.get("row_policies", [])],
        )


if __name__ == "__main__":  # pragma: no cover
    from kronicle_sdk.utils.log import log_d

    here = "kron_permissions.tests"
    perms = KroniclePermissions.from_json(
        {
            "direct_roles": [
                {
                    "id": "d0332ec8-78ba-476c-99b5-cfc0af17fda7",
                    "name": "Writer",
                    "permissions": ["channel:read"],
                },
            ],
            "group_roles": [
                {
                    "group": {
                        "id": "e1e90f77-5e14-4a1d-a2f8-2a5a420e6c1e",
                        "name": "Admins",
                    },
                    "role": {
                        "id": "f0332ec8-78ba-476c-99b5-cfc0af17fda7",
                        "name": "Reader",
                        "permissions": ["channel:read"],
                    },
                },
            ],
            "zone_policies": [],
            "channel_policies": [],
            "row_policies": [],
        }
    )
    log_d(here, f"Permissions: {perms}")
