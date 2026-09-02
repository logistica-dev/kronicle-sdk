# tests/models/test_kronicle_role.py
from uuid import UUID, uuid4

import pytest

from kronicle_sdk.models.rbac.kronicle_role import KronicleRole


class TestKronicleRoleValidation:
    def test_minimal_ok(self):
        r = KronicleRole(name="test.role")
        assert r.name == "test.role"
        assert r.permissions is None

    def test_with_all_fields(self):
        rid = uuid4()
        r = KronicleRole(
            id=rid,
            name="admin",
            description="Full access",
            permissions=["channel:read", "channel:write"],
            restrictions=["rbac:delete"],
            details={"env": "prod"},
        )
        assert r.id == rid
        assert r.permissions == ["channel:read", "channel:write"]

    def test_auto_id_when_missing(self):
        r = KronicleRole(name="auto")
        assert isinstance(r.id, UUID)

    def test_name_too_short(self):
        with pytest.raises(ValueError):
            KronicleRole(name="ab")

    def test_name_invalid_chars(self):
        with pytest.raises(ValueError):
            KronicleRole(name="bad name!")

    def test_name_none_is_ok(self):
        r = KronicleRole()
        assert r.name is None

    def test_details_too_large(self):
        with pytest.raises(ValueError, match="too large"):
            KronicleRole(name="test.role", details={"big": "x" * (70 * 1024)})

    def test_details_none_and_small_ok(self):
        assert KronicleRole(name="test.role").details is None
        r = KronicleRole(name="test.role", details={"env": "prod"})
        assert r.details == {"env": "prod"}


class TestKronicleRoleSerialization:
    def test_to_json_minimal(self):
        r = KronicleRole(name="test.role")
        d = r.model_dump()
        assert d["name"] == "test.role"
        assert "id" in d

    def test_to_json_skip_nones(self):
        r = KronicleRole(name="test.role", permissions=["channel:read"])
        d = r.model_dump()
        assert d["name"] == "test.role"
        assert d["permissions"] == ["channel:read"]
        assert "description" not in d

    def test_roundtrip(self):
        r1 = KronicleRole(name="roundtrip", permissions=["channel:read"], description="desc")
        r2 = KronicleRole(**r1.model_dump())
        assert r2.name == "roundtrip"
        assert r2.permissions == ["channel:read"]
        assert r2.description == "desc"

    def test_str(self):
        r = KronicleRole(name="test.role")
        s = str(r)
        assert "test.role" in s
        assert "Role" in s
