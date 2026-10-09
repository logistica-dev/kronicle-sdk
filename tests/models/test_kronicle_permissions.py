# tests/models/test_kronicle_permissions.py
from uuid import uuid4

from kronicle_sdk.models.rbac.kronicle_permissions import (
    KronicleGroupRole,
    KroniclePermissions,
)


class TestKronicleGroupRole:
    def test_from_json(self):
        gr = KronicleGroupRole.from_json(
            {
                "group": {"name": "Admins"},
                "role": {"name": "Reader", "permissions": ["channel:read"]},
            }
        )
        assert isinstance(gr, KronicleGroupRole)
        assert gr.group.name == "Admins"
        assert gr.role.name == "Reader"


class TestKroniclePermissions:
    def test_defaults_are_empty_lists(self):
        perms = KroniclePermissions()
        assert perms.direct_roles == []
        assert perms.group_roles == []
        assert perms.zone_policies == []
        assert perms.channel_policies == []
        assert perms.row_policies == []

    def test_from_json_empty(self):
        perms = KroniclePermissions.from_json({})
        assert perms.direct_roles == []
        assert perms.group_roles == []

    def test_from_json_direct_and_group_roles(self):
        perms = KroniclePermissions.from_json(
            {
                "direct_roles": [
                    {"id": str(uuid4()), "name": "Writer", "permissions": ["channel:read"]},
                ],
                "group_roles": [
                    {
                        "group": {"name": "Admins"},
                        "role": {"name": "Reader", "permissions": ["channel:read"]},
                    },
                ],
            }
        )
        assert perms.direct_roles[0].name == "Writer"
        assert perms.group_roles[0].group.name == "Admins"
        assert perms.group_roles[0].role.name == "Reader"

    def test_from_json_direct_role_wrapped_in_role_key(self):
        # `r.get("role") or r`: a wrapper dict is unwrapped to the inner role.
        perms = KroniclePermissions.from_json(
            {"direct_roles": [{"role": {"name": "Writer", "permissions": ["channel:read"]}}]}
        )
        assert perms.direct_roles[0].name == "Writer"
