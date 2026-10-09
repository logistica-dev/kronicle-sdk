# tests/connectors/test_rbac_setup.py
"""Residual coverage for rbac_setup.py: users, groups, role extras, put override,
relationship helpers, permissions, access profiles and policies."""

from typing import Any
from uuid import uuid4

import pytest

from kronicle_sdk.connectors.rbac.rbac_setup import KronicleRbac
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.kronicle_errors import KronicleHTTPError, KronicleHTTPErrorModel
from kronicle_sdk.models.rbac.kronicle_access_profile import (
    KronicleChannelAccess,
    KronicleRowAccess,
    KronicleZoneAccess,
)
from kronicle_sdk.models.rbac.kronicle_group import KronicleGroup
from kronicle_sdk.models.rbac.kronicle_permissions import KroniclePermissions
from kronicle_sdk.models.rbac.kronicle_policy import (
    KronicleChannelPolicy,
    KronicleRowPolicy,
    KronicleSubject,
    KronicleZonePolicy,
)
from kronicle_sdk.models.rbac.kronicle_role import KronicleRole
from kronicle_sdk.models.rbac.kronicle_row import KronicleRow
from kronicle_sdk.models.rbac.kronicle_user import KronicleUser
from kronicle_sdk.models.rbac.kronicle_zone import KronicleZone


@pytest.fixture
def rbac():
    return KronicleRbac(url="http://localhost:8765", usr="admin", pwd="secret")


# ----------------------------------------------------------------------------------------------
# Shared dict builders
# ----------------------------------------------------------------------------------------------
def _user_dict(**over: Any) -> dict:
    d: dict[str, Any] = {"id": str(uuid4()), "name": "Alice", "email": "alice@example.com"}
    d.update(over)
    return d


def _group_dict(**over: Any) -> dict:
    d: dict[str, Any] = {"id": str(uuid4()), "name": "Admins"}
    d.update(over)
    return d


def _role_dict(**over: Any) -> dict:
    d: dict[str, Any] = {"id": str(uuid4()), "name": "Reader", "permissions": ["data:access"]}
    d.update(over)
    return d


def _zone_access_dict(role_id, zone_id, description=None) -> dict:
    return {
        "id": str(uuid4()),
        "name": "Zone acc",
        "details": None,
        "description": description,
        "role": _role_dict(id=str(role_id), name="Reader"),
        "zone": {"id": str(zone_id), "name": "ZoneA", "details": {"init": True}},
    }


def _channel_access_dict(role_id, channel_id, description=None) -> dict:
    return {
        "id": str(uuid4()),
        "name": "Channel acc",
        "details": None,
        "description": description,
        "role": _role_dict(id=str(role_id), name="Writer"),
        "channel": {"id": str(channel_id), "name": "Channel_1", "details": None},
    }


def _row_access_dict(role_id, row_id, channel_id, description=None) -> dict:
    return {
        "id": str(uuid4()),
        "name": "Row acc",
        "details": None,
        "description": description,
        "role": _role_dict(id=str(role_id), name="Writer"),
        "row": {"id": row_id, "channel_id": str(channel_id), "name": "Row_1", "details": None},
    }


def _subject_dict() -> dict:
    return {"id": str(uuid4()), "name": "Scoped", "details": None, "type": "group", "group_id": str(uuid4())}


def _zone_policy_dict(role_id, zone_id, **over: Any) -> dict:
    d = {
        "id": str(uuid4()),
        "name": "Zone policy",
        "details": None,
        "description": None,
        "is_delegation": False,
        "delegation_start": None,
        "delegation_end": None,
        "subject": _subject_dict(),
        "access_profile": _zone_access_dict(role_id, zone_id),
    }
    d.update(over)
    return d


def _channel_policy_dict(role_id, channel_id, **over: Any) -> dict:
    d = {
        "id": str(uuid4()),
        "name": "Channel policy",
        "details": None,
        "description": None,
        "is_delegation": False,
        "delegation_start": None,
        "delegation_end": None,
        "subject": _subject_dict(),
        "access_profile": _channel_access_dict(role_id, channel_id),
    }
    d.update(over)
    return d


def _row_policy_dict(role_id, row_id, channel_id, **over: Any) -> dict:
    d = {
        "id": str(uuid4()),
        "name": "Row policy",
        "details": None,
        "description": None,
        "is_delegation": False,
        "delegation_start": None,
        "delegation_end": None,
        "subject": _subject_dict(),
        "access_profile": _row_access_dict(role_id, row_id, channel_id),
    }
    d.update(over)
    return d


def _http_error(status: int) -> KronicleHTTPError:
    return KronicleHTTPError(KronicleHTTPErrorModel(status=status, error="Err", message="msg", url="/x"))


def _raise_status(status: int):
    def _mock_get(*, route, **kw):
        raise _http_error(status)

    return _mock_get


def _zone_policy_obj(role_id, zone_id, *, name=None, policy_id=None) -> KronicleZonePolicy:
    return KronicleZonePolicy(
        id=policy_id,
        name=name,
        subject=KronicleSubject(type="group", name="Scoped", group_id=uuid4()),
        access_profile=KronicleZoneAccess(
            role=KronicleRole(id=role_id, name="Reader"),
            zone=KronicleZone(id=zone_id, name="ZoneA"),
        ),
    )


def _channel_policy_obj(role_id, channel_id, *, name=None, policy_id=None) -> KronicleChannelPolicy:
    return KronicleChannelPolicy(
        id=policy_id,
        name=name,
        subject=KronicleSubject(type="group", name="Scoped", group_id=uuid4()),
        access_profile=KronicleChannelAccess(
            role=KronicleRole(id=role_id, name="Writer"),
            channel=KronicleChannel(id=channel_id, name="Channel_1"),
        ),
    )


def _row_policy_obj(role_id, row_id, channel_id, *, name=None, policy_id=None) -> KronicleRowPolicy:
    return KronicleRowPolicy(
        id=policy_id,
        name=name,
        subject=KronicleSubject(type="group", name="Scoped", group_id=uuid4()),
        access_profile=KronicleRowAccess(
            role=KronicleRole(id=role_id, name="Writer"),
            row=KronicleRow(id=row_id, channel_id=channel_id, name="Row_1"),
        ),
    )


# ----------------------------------------------------------------------------------------------
# Prefix
# ----------------------------------------------------------------------------------------------
class TestKronicleRbacMeta:
    def test_prefix(self, rbac):
        assert rbac.prefix == "/rbac/v1"


# ----------------------------------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------------------------------
class TestKronicleRbacUsers:
    def test_list_users_default(self, rbac, monkeypatch):
        def mock_get(*, route, **kw):
            assert route == "/users"
            return [_user_dict()]

        monkeypatch.setattr(rbac, "get", mock_get)
        users = rbac.list_users()
        assert len(users) == 1
        assert isinstance(users[0], KronicleUser)

    def test_list_users_include_inactive(self, rbac, monkeypatch):
        def mock_get(*, route, **kw):
            assert route == "/users?include_inactive=1"
            return []

        monkeypatch.setattr(rbac, "get", mock_get)
        assert rbac.list_users(include_inactive=True) == []

    def test_get_user_by_id_found(self, rbac, monkeypatch):
        uid = uuid4()
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: _user_dict(id=str(uid)))
        user = rbac.get_user_by_id(user_id=uid)
        assert user is not None
        assert user.id == uid

    def test_get_user_by_id_not_found(self, rbac, monkeypatch):
        def mock_get(*, route, **kw):
            raise _http_error(404)

        monkeypatch.setattr(rbac, "get", mock_get)
        assert rbac.get_user_by_id(user_id=uuid4()) is None

    def test_get_user_by_id_reraises_non_404(self, rbac, monkeypatch):
        def mock_get(*, route, **kw):
            raise _http_error(500)

        monkeypatch.setattr(rbac, "get", mock_get)
        with pytest.raises(KronicleHTTPError):
            rbac.get_user_by_id(user_id=uuid4())

    def test_get_user_by_email(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: _user_dict())
        user = rbac.get_user_by_email(email="alice@example.com")
        assert user is not None and user.email == "alice@example.com"

    def test_get_user_by_email_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: None)
        assert rbac.get_user_by_email(email="none@example.com") is None

    def test_get_user_by_name(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: _user_dict())
        user = rbac.get_user_by_name(name="Alice")
        assert user is not None and user.name == "Alice"

    def test_get_user_by_name_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: None)
        assert rbac.get_user_by_name(name="Nobody") is None

    def test_get_user_by_orcid(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: _user_dict(orcid="0000-0002-1825-0097"))
        user = rbac.get_user_by_orcid(orcid="0000-0002-1825-0097")
        assert user is not None and user.orcid == "0000-0002-1825-0097"

    def test_get_user_by_orcid_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: None)
        assert rbac.get_user_by_orcid(orcid="0000-0000-0000-0000") is None

    def test_get_user_prefers_id(self, rbac, monkeypatch):
        existing = KronicleUser(**_user_dict())
        monkeypatch.setattr(rbac, "get_user_by_id", lambda **kw: existing)
        result = rbac.get_user(KronicleUser(**_user_dict()))
        assert result is existing

    def test_get_user_falls_back_to_email(self, rbac, monkeypatch):
        existing = KronicleUser(**_user_dict())
        monkeypatch.setattr(rbac, "get_user_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_user_by_email", lambda **kw: existing)
        result = rbac.get_user(KronicleUser(**_user_dict()))
        assert result is existing

    def test_get_user_falls_back_to_name(self, rbac, monkeypatch):
        existing = KronicleUser(**_user_dict())
        monkeypatch.setattr(rbac, "get_user_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_user_by_email", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_user_by_name", lambda **kw: existing)
        result = rbac.get_user(KronicleUser(**_user_dict()))
        assert result is existing

    def test_get_user_falls_back_to_orcid(self, rbac, monkeypatch):
        existing = KronicleUser(**_user_dict(orcid="0000-0002-1825-0097"))
        monkeypatch.setattr(rbac, "get_user_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_user_by_email", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_user_by_name", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_user_by_orcid", lambda **kw: existing)
        result = rbac.get_user(KronicleUser(**_user_dict(orcid="0000-0002-1825-0097")))
        assert result is existing

    def test_get_user_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get_user_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_user_by_email", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_user_by_name", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_user_by_orcid", lambda **kw: None)
        assert rbac.get_user(KronicleUser(**_user_dict())) is None

    def test_create_user_existing(self, rbac, monkeypatch):
        existing = KronicleUser(**_user_dict())
        monkeypatch.setattr(rbac, "get_user", lambda user: existing)

        def raise_post(*, route, body, **kw):
            raise AssertionError("post should not have been called")

        monkeypatch.setattr(rbac, "post", raise_post)
        assert rbac.create_user(KronicleUser(**_user_dict())) is existing

    def test_create_user_new(self, rbac, monkeypatch):
        created = _user_dict(name="Bobby", email="bobby@example.com")
        monkeypatch.setattr(rbac, "get_user", lambda user: None)

        def mock_post(*, route, body, **kw):
            assert route == "/users"
            assert body["email"] == "bobby@example.com"
            return created

        monkeypatch.setattr(rbac, "post", mock_post)
        user = rbac.create_user(KronicleUser(name="Bobby", email="bobby@example.com"))
        assert user.name == "Bobby"

    def test_patch_user(self, rbac, monkeypatch):
        uid = uuid4()
        fake = _user_dict(id=str(uid), name="Bobby")

        def mock_patch(*, route, body, **kw):
            assert str(uid) in route
            return fake

        monkeypatch.setattr(rbac, "patch", mock_patch)
        user = rbac.patch_user(KronicleUser(id=uid, name="Bobby", email="bobby@example.com"))
        assert user.name == "Bobby"

    def test_deactivate_user(self, rbac, monkeypatch):
        uid = uuid4()

        def mock_delete(*, route, **kw):
            assert str(uid) in route
            return _user_dict(id=str(uid), is_active=False)

        monkeypatch.setattr(rbac, "delete", mock_delete)
        user = rbac.deactivate_user(user_id=uid)
        assert user.id == uid

    def test_delete_user(self, rbac, monkeypatch):
        uid = uuid4()

        def mock_delete(*, route, **kw):
            assert str(uid) in route
            assert "remove=true" in route
            return _user_dict(id=str(uid))

        monkeypatch.setattr(rbac, "delete", mock_delete)
        assert rbac.delete_user(user_id=uid).id == uid


# ----------------------------------------------------------------------------------------------
# Groups
# ----------------------------------------------------------------------------------------------
class TestKronicleRbacGroups:
    def test_list_groups(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: [_group_dict()])
        groups = rbac.list_groups()
        assert len(groups) == 1 and isinstance(groups[0], KronicleGroup)

    def test_get_group_by_id_found(self, rbac, monkeypatch):
        gid = uuid4()
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: _group_dict(id=str(gid)))
        group = rbac.get_group_by_id(group_id=gid)
        assert group is not None and group.id == gid

    def test_get_group_by_id_not_found(self, rbac, monkeypatch):
        def mock_get(*, route, **kw):
            raise _http_error(404)

        monkeypatch.setattr(rbac, "get", mock_get)
        assert rbac.get_group_by_id(group_id=uuid4()) is None

    def test_get_group_by_id_reraises_non_404(self, rbac, monkeypatch):
        def mock_get(*, route, **kw):
            raise _http_error(500)

        monkeypatch.setattr(rbac, "get", mock_get)
        with pytest.raises(KronicleHTTPError):
            rbac.get_group_by_id(group_id=uuid4())

    def test_get_group_by_name(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: _group_dict())
        assert rbac.get_group_by_name(name="Admins") is not None

    def test_get_group_id_branch(self, rbac, monkeypatch):
        existing = KronicleGroup(**_group_dict())
        monkeypatch.setattr(rbac, "get_group_by_id", lambda **kw: existing)
        assert rbac.get_group(KronicleGroup(**_group_dict())) is existing

    def test_get_group_name_branch(self, rbac, monkeypatch):
        existing = KronicleGroup(**_group_dict())
        monkeypatch.setattr(rbac, "get_group_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_group_by_name", lambda **kw: existing)
        assert rbac.get_group(KronicleGroup(**_group_dict())) is existing

    def test_get_group_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get_group_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_group_by_name", lambda **kw: None)
        assert rbac.get_group(KronicleGroup(**_group_dict())) is None

    def test_create_group_existing(self, rbac, monkeypatch):
        existing = KronicleGroup(**_group_dict())
        monkeypatch.setattr(rbac, "get_group", lambda group: existing)

        def raise_post(*, route, body, **kw):
            raise AssertionError("post should not have been called")

        monkeypatch.setattr(rbac, "post", raise_post)
        assert rbac.create_group(KronicleGroup(**_group_dict())) is existing

    def test_create_group_new(self, rbac, monkeypatch):
        created = _group_dict(name="Editors")
        monkeypatch.setattr(rbac, "get_group", lambda group: None)

        def mock_post(*, route, body, **kw):
            assert route == "/groups"
            return created

        monkeypatch.setattr(rbac, "post", mock_post)
        assert rbac.create_group(KronicleGroup(name="Editors")).name == "Editors"

    def test_patch_group(self, rbac, monkeypatch):
        gid = uuid4()
        monkeypatch.setattr(rbac, "patch", lambda *, route, body, **kw: _group_dict(id=str(gid), name="Updated"))
        group = rbac.patch_group(KronicleGroup(id=gid, name="Updated"))
        assert group.name == "Updated"

    def test_delete_group_no_force(self, rbac, monkeypatch):
        gid = uuid4()

        def mock_delete(*, route, **kw):
            assert route == f"/groups/{gid}"
            return _group_dict(id=str(gid))

        monkeypatch.setattr(rbac, "delete", mock_delete)
        assert rbac.delete_group(group_id=gid).id == gid

    def test_delete_group_force(self, rbac, monkeypatch):
        gid = uuid4()

        def mock_delete(*, route, **kw):
            assert route == f"/groups/{gid}?force=true"
            return _group_dict(id=str(gid))

        monkeypatch.setattr(rbac, "delete", mock_delete)
        assert rbac.delete_group(group_id=gid, force=True).id == gid

    def test_delete_group_with_name_missing(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get_group_by_name", lambda name: None)

        def raise_delete(*, route, **kw):
            raise AssertionError("delete should not have been called")

        monkeypatch.setattr(rbac, "delete", raise_delete)
        assert rbac.delete_group_with_name("Ghost") is None

    def test_delete_group_with_name_found(self, rbac, monkeypatch):
        gid = uuid4()
        monkeypatch.setattr(rbac, "get_group_by_name", lambda name: KronicleGroup(id=gid, name="Admins"))
        monkeypatch.setattr(rbac, "delete", lambda *, route, **kw: _group_dict(id=str(gid)))
        assert rbac.delete_group_with_name("Admins").id == gid

    def test_delete_group_with_name_found_force(self, rbac, monkeypatch):
        gid = uuid4()
        captured = {}

        def mock_delete(*, route, **kw):
            captured["route"] = route
            return _group_dict(id=str(gid))

        monkeypatch.setattr(rbac, "get_group_by_name", lambda name: KronicleGroup(id=gid, name="Admins"))
        monkeypatch.setattr(rbac, "delete", mock_delete)
        rbac.delete_group_with_name("Admins", force=True)
        assert captured["route"] == f"/groups/{gid}?force=true"

    def test_get_users_from_group_empty(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: [])
        assert rbac.get_users_from_group(group_id=uuid4()) == []

    def test_get_users_from_group_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: None)
        assert rbac.get_users_from_group(group_id=uuid4()) == []

    def test_get_users_from_group_populated(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: [_user_dict()])
        users = rbac.get_users_from_group(group_id=uuid4())
        assert len(users) == 1 and isinstance(users[0], KronicleUser)

    def test_add_user_to_group(self, rbac, monkeypatch):
        gid, uid = uuid4(), uuid4()
        captured = {}

        def mock_post(*, route, **kw):
            captured["route"] = route
            return {"detail": "added"}

        monkeypatch.setattr(rbac, "post", mock_post)
        result = rbac.add_user_to_group(group_id=gid, user_id=uid)
        assert result["detail"] == "added"
        assert captured["route"] == f"/groups/{gid}/users?user_id={uid}"

    def test_remove_user_from_group(self, rbac, monkeypatch):
        gid, uid = uuid4(), uuid4()
        captured = {}

        def mock_delete(*, route, **kw):
            captured["route"] = route
            return {"detail": "removed"}

        monkeypatch.setattr(rbac, "delete", mock_delete)
        result = rbac.remove_user_from_group(group_id=gid, user_id=uid)
        assert result["detail"] == "removed"
        assert captured["route"] == f"/groups/{gid}/users/{uid}"


# ----------------------------------------------------------------------------------------------
# Roles (residual)
# ----------------------------------------------------------------------------------------------
class TestKronicleRbacRolesResidual:
    def test_get_role_by_id_reraises_non_404(self, rbac, monkeypatch):
        def mock_get(*, route, **kw):
            raise _http_error(500)

        monkeypatch.setattr(rbac, "get", mock_get)
        with pytest.raises(KronicleHTTPError):
            rbac.get_role_by_id(role_id=uuid4())

    def test_get_role_id_branch(self, rbac, monkeypatch):
        existing = KronicleRole(**_role_dict())
        monkeypatch.setattr(rbac, "get_role_by_id", lambda **kw: existing)
        assert rbac.get_role(KronicleRole(**_role_dict())) is existing

    def test_get_role_name_branch(self, rbac, monkeypatch):
        existing = KronicleRole(**_role_dict())
        monkeypatch.setattr(rbac, "get_role_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_role_by_name", lambda **kw: existing)
        assert rbac.get_role(KronicleRole(**_role_dict())) is existing

    def test_get_role_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get_role_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_role_by_name", lambda **kw: None)
        assert rbac.get_role(KronicleRole(**_role_dict())) is None

    def test_create_role_existing(self, rbac, monkeypatch):
        existing = KronicleRole(**_role_dict())
        monkeypatch.setattr(rbac, "get_role", lambda role: existing)

        def raise_post(*, route, body, **kw):
            raise AssertionError("post should not have been called")

        monkeypatch.setattr(rbac, "post", raise_post)
        assert rbac.create_role(KronicleRole(**_role_dict())) is existing

    def test_delete_role_force(self, rbac, monkeypatch):
        rid = uuid4()
        captured = {}

        def mock_delete(*, route, **kw):
            captured["route"] = route
            return _role_dict(id=str(rid))

        monkeypatch.setattr(rbac, "delete", mock_delete)
        rbac.delete_role(role_id=rid, force=True)
        assert captured["route"] == f"/roles/{rid}?force=true"

    def test_delete_role_with_name_missing(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get_role_by_name", lambda name: None)

        def raise_delete(*, route, **kw):
            raise AssertionError("delete should not have been called")

        monkeypatch.setattr(rbac, "delete", raise_delete)
        assert rbac.delete_role_with_name("Ghost") is None

    def test_delete_role_with_name_found(self, rbac, monkeypatch):
        rid = uuid4()
        monkeypatch.setattr(rbac, "get_role_by_name", lambda name: KronicleRole(id=rid, name="Reader"))
        monkeypatch.setattr(rbac, "delete", lambda *, route, **kw: _role_dict(id=str(rid)))
        assert rbac.delete_role_with_name("Reader").id == rid

    def test_delete_role_with_name_found_force(self, rbac, monkeypatch):
        rid = uuid4()
        captured = {}

        def mock_delete(*, route, **kw):
            captured["route"] = route
            return _role_dict(id=str(rid))

        monkeypatch.setattr(rbac, "get_role_by_name", lambda name: KronicleRole(id=rid, name="Reader"))
        monkeypatch.setattr(rbac, "delete", mock_delete)
        rbac.delete_role_with_name("Reader", force=True)
        assert captured["route"] == f"/roles/{rid}?force=true"

    def test_remove_role_from_user(self, rbac, monkeypatch):
        rid, uid = uuid4(), uuid4()
        monkeypatch.setattr(rbac, "delete", lambda *, route, **kw: {"detail": "removed"})
        assert rbac.remove_role_from_user(role_id=rid, user_id=uid)["detail"] == "removed"

    def test_remove_role_from_group(self, rbac, monkeypatch):
        rid, gid = uuid4(), uuid4()
        monkeypatch.setattr(rbac, "delete", lambda *, route, **kw: {"detail": "removed"})
        assert rbac.remove_role_from_group(role_id=rid, group_id=gid)["detail"] == "removed"


# ----------------------------------------------------------------------------------------------
# put() override + role assignments (exercised through the real put -> _request)
# ----------------------------------------------------------------------------------------------
class TestKronicleRbacPutOverride:
    def test_put_with_body(self, rbac, monkeypatch):
        captured: dict[str, Any] = {}

        def fake_request(method, route=None, body=None, *, prefix=None, **kwargs):
            captured["method"] = method
            captured["route"] = route
            captured["body"] = body
            captured["prefix"] = prefix
            captured["timeout"] = kwargs.get("timeout")
            return {"ok": True}

        monkeypatch.setattr(rbac, "_request", fake_request)
        result = rbac.put(route="/foo", body={"a": 1})
        assert result == {"ok": True}
        assert captured["route"] == "/foo"
        assert captured["body"] == {"a": 1}
        assert captured["prefix"] is None
        assert captured["timeout"] == rbac.timeout

    def test_put_bodyless(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "_request", lambda *a, **kw: {"ok": True})
        assert rbac.put(route="/foo") == {"ok": True}

    def test_assign_role_to_user(self, rbac, monkeypatch):
        rid, uid = uuid4(), uuid4()
        captured: dict[str, Any] = {}

        def fake_request(method, route=None, body=None, **kwargs):
            captured["route"] = route
            captured["body"] = body
            return {"detail": "assigned"}

        monkeypatch.setattr(rbac, "_request", fake_request)
        result = rbac.assign_role_to_user(role_id=rid, user_id=uid)
        assert result["detail"] == "assigned"
        assert captured["route"] == f"/users/{uid}/roles/{rid}"
        assert captured["body"] is None

    def test_assign_role_to_group(self, rbac, monkeypatch):
        rid, gid = uuid4(), uuid4()
        captured: dict[str, Any] = {}

        def fake_request(method, route=None, body=None, **kwargs):
            captured["route"] = route
            return {"detail": "assigned"}

        monkeypatch.setattr(rbac, "_request", fake_request)
        result = rbac.assign_role_to_group(role_id=rid, group_id=gid)
        assert result["detail"] == "assigned"
        assert captured["route"] == f"/groups/{gid}/roles/{rid}"


# ----------------------------------------------------------------------------------------------
# Relationship helpers + permissions
# ----------------------------------------------------------------------------------------------
class TestKronicleRbacRelationshipExtras:
    def test_get_groups_for_user(self, rbac, monkeypatch):
        uid = uuid4()

        def mock_get(*, route, params=None, **kw):
            assert str(uid) in route
            assert params is None
            return [_group_dict()]

        monkeypatch.setattr(rbac, "get", mock_get)
        groups = rbac.get_groups_for_user(user_id=uid)
        assert len(groups) == 1 and isinstance(groups[0], KronicleGroup)

    def test_get_groups_for_user_indirect(self, rbac, monkeypatch):
        def mock_get(*, route, params=None, **kw):
            assert params == {"indirect": "1"}
            return [_group_dict(name="Admins"), _group_dict(name="Editors")]

        monkeypatch.setattr(rbac, "get", mock_get)
        groups = rbac.get_groups_for_user(user_id=uuid4(), indirect=True)
        assert [g.name for g in groups] == ["Admins", "Editors"]


class TestKronicleRbacPermissions:
    def test_get_user_permissions(self, rbac, monkeypatch):
        uid = uuid4()

        def mock_get(*, route, **kw):
            assert route == f"/users/{uid}/permissions"
            return {"direct_roles": [{"role": _role_dict()}], "group_roles": [], "zone_policies": []}

        monkeypatch.setattr(rbac, "get", mock_get)
        perms = rbac.get_user_permissions(user_id=uid)
        assert isinstance(perms, KroniclePermissions)
        assert len(perms.direct_roles) == 1

    def test_get_group_permissions(self, rbac, monkeypatch):
        gid = uuid4()

        def mock_get(*, route, **kw):
            assert route == f"/groups/{gid}/permissions"
            return {}

        monkeypatch.setattr(rbac, "get", mock_get)
        perms = rbac.get_group_permissions(group_id=gid)
        assert isinstance(perms, KroniclePermissions)


# ----------------------------------------------------------------------------------------------
# Access profiles
# ----------------------------------------------------------------------------------------------
class TestKronicleRbacAccessProfiles:
    def test_list_access_profiles(self, rbac, monkeypatch):
        rid, zid, cid = uuid4(), uuid4(), uuid4()
        fake = {
            "zone": [_zone_access_dict(rid, zid)],
            "channel": [_channel_access_dict(rid, cid)],
            "row": [_row_access_dict(rid, 42, cid)],
        }

        def mock_get(*, route, **kw):
            assert route == "/access-profiles"
            return fake

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.list_access_profiles()
        assert set(result) == {"zone", "channel", "row"}
        assert isinstance(result["zone"][0], KronicleZoneAccess)
        assert isinstance(result["channel"][0], KronicleChannelAccess)
        assert isinstance(result["row"][0], KronicleRowAccess)

    def test_list_access_profiles_empty(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: {})
        result = rbac.list_access_profiles()
        assert result == {"zone": [], "channel": [], "row": []}

    # --- zone ---
    def test_create_zone_access_profile(self, rbac, monkeypatch):
        rid, zid = uuid4(), uuid4()
        fake = _zone_access_dict(rid, zid, description="desc")

        def mock_post(*, route, body, **kw):
            assert route == "/access-profiles/zones"
            return fake

        monkeypatch.setattr(rbac, "post", mock_post)
        access = KronicleZoneAccess(
            role=KronicleRole(id=rid, name="Reader"),
            zone=KronicleZone(id=zid, name="ZoneA"),
            description="desc",
        )
        result = rbac.create_zone_access_profile(access)
        assert isinstance(result, KronicleZoneAccess) and result.zone.id == zid

    def test_list_zone_access_profiles_non_empty(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: [_zone_access_dict(uuid4(), uuid4())])
        assert len(rbac.list_zone_access_profiles()) == 1

    def test_list_zone_access_profiles_empty(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: None)
        assert rbac.list_zone_access_profiles() == []

    def test_get_zone_access_profile(self, rbac, monkeypatch):
        pid, zid = uuid4(), uuid4()
        fake = _zone_access_dict(uuid4(), zid)
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: fake)
        result = rbac.get_zone_access_profile(profile_id=pid)
        assert isinstance(result, KronicleZoneAccess)

    def test_get_zone_access_profile_by_name(self, rbac, monkeypatch):
        fake = _zone_access_dict(uuid4(), uuid4())
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: fake)
        result = rbac.get_zone_access_profile_by_name("Zone acc")
        assert isinstance(result, KronicleZoneAccess)

    def test_get_zone_access_profile_by_name_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: None)
        assert rbac.get_zone_access_profile_by_name("Ghost") is None

    def test_patch_zone_access_profile(self, rbac, monkeypatch):
        pid, zid = uuid4(), uuid4()

        def mock_patch(*, route, body, **kw):
            assert str(pid) in route
            return _zone_access_dict(uuid4(), zid)

        monkeypatch.setattr(rbac, "patch", mock_patch)
        access = KronicleZoneAccess(
            id=pid, role=KronicleRole(id=uuid4(), name="Reader"), zone=KronicleZone(id=zid, name="ZoneA")
        )
        assert isinstance(rbac.patch_zone_access_profile(access), KronicleZoneAccess)

    def test_delete_zone_access_profile(self, rbac, monkeypatch):
        pid = uuid4()
        monkeypatch.setattr(rbac, "delete", lambda *, route, **kw: _zone_access_dict(uuid4(), uuid4()))
        assert isinstance(rbac.delete_zone_access_profile(profile_id=pid), KronicleZoneAccess)

    # --- channel ---
    def test_create_channel_access_profile(self, rbac, monkeypatch):
        rid, cid = uuid4(), uuid4()
        fake = _channel_access_dict(rid, cid)

        def mock_post(*, route, body, **kw):
            assert route == "/access-profiles/channels"
            return fake

        monkeypatch.setattr(rbac, "post", mock_post)
        access = KronicleChannelAccess(
            role=KronicleRole(id=rid, name="Writer"), channel=KronicleChannel(id=cid, name="Channel_1")
        )
        assert rbac.create_channel_access_profile(access).channel.id == cid

    def test_list_channel_access_profiles_non_empty(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: [_channel_access_dict(uuid4(), uuid4())])
        assert len(rbac.list_channel_access_profiles()) == 1

    def test_list_channel_access_profiles_empty(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: None)
        assert rbac.list_channel_access_profiles() == []

    def test_get_channel_access_profile(self, rbac, monkeypatch):
        pid, cid = uuid4(), uuid4()
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: _channel_access_dict(uuid4(), cid))
        assert isinstance(rbac.get_channel_access_profile(profile_id=pid), KronicleChannelAccess)

    def test_get_channel_access_profile_by_name(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: _channel_access_dict(uuid4(), uuid4()))
        assert isinstance(rbac.get_channel_access_profile_by_name("Channel acc"), KronicleChannelAccess)

    def test_get_channel_access_profile_by_name_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: None)
        assert rbac.get_channel_access_profile_by_name("Ghost") is None

    def test_patch_channel_access_profile(self, rbac, monkeypatch):
        pid, cid = uuid4(), uuid4()

        def mock_patch(*, route, body, **kw):
            assert str(pid) in route
            return _channel_access_dict(uuid4(), cid)

        monkeypatch.setattr(rbac, "patch", mock_patch)
        access = KronicleChannelAccess(
            id=pid,
            role=KronicleRole(id=uuid4(), name="Writer"),
            channel=KronicleChannel(id=cid, name="Channel_1"),
        )
        assert isinstance(rbac.patch_channel_access_profile(access), KronicleChannelAccess)

    def test_delete_channel_access_profile(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "delete", lambda *, route, **kw: _channel_access_dict(uuid4(), uuid4()))
        assert isinstance(rbac.delete_channel_access_profile(profile_id=uuid4()), KronicleChannelAccess)

    # --- row ---
    def test_create_row_access_profile(self, rbac, monkeypatch):
        rid, cid = uuid4(), uuid4()
        fake = _row_access_dict(rid, 42, cid)

        def mock_post(*, route, body, **kw):
            assert route == "/access-profiles/rows"
            return fake

        monkeypatch.setattr(rbac, "post", mock_post)
        access = KronicleRowAccess(
            role=KronicleRole(id=rid, name="Writer"),
            row=KronicleRow(id=42, channel_id=cid, name="Row_1"),
        )
        assert rbac.create_row_access_profile(access).row.id == 42

    def test_list_row_access_profiles_non_empty(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: [_row_access_dict(uuid4(), 42, uuid4())])
        assert len(rbac.list_row_access_profiles()) == 1

    def test_list_row_access_profiles_empty(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: None)
        assert rbac.list_row_access_profiles() == []

    def test_get_row_access_profile(self, rbac, monkeypatch):
        cid = uuid4()
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: _row_access_dict(uuid4(), 7, cid))
        assert isinstance(rbac.get_row_access_profile(profile_id=uuid4()), KronicleRowAccess)

    def test_get_row_access_profile_by_name(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: _row_access_dict(uuid4(), 7, uuid4()))
        assert isinstance(rbac.get_row_access_profile_by_name("Row acc"), KronicleRowAccess)

    def test_get_row_access_profile_by_name_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: None)
        assert rbac.get_row_access_profile_by_name("Ghost") is None

    def test_patch_row_access_profile(self, rbac, monkeypatch):
        pid, cid = uuid4(), uuid4()

        def mock_patch(*, route, body, **kw):
            assert str(pid) in route
            return _row_access_dict(uuid4(), 7, cid)

        monkeypatch.setattr(rbac, "patch", mock_patch)
        access = KronicleRowAccess(
            id=pid,
            role=KronicleRole(id=uuid4(), name="Writer"),
            row=KronicleRow(id=7, channel_id=cid, name="Row_1"),
        )
        assert isinstance(rbac.patch_row_access_profile(access), KronicleRowAccess)

    def test_delete_row_access_profile(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "delete", lambda *, route, **kw: _row_access_dict(uuid4(), 7, uuid4()))
        assert isinstance(rbac.delete_row_access_profile(profile_id=uuid4()), KronicleRowAccess)


# ----------------------------------------------------------------------------------------------
# Policies
# ----------------------------------------------------------------------------------------------
class TestKronicleRbacPolicies:
    def test_list_policies(self, rbac, monkeypatch):
        fake = {
            "zone": [_zone_policy_dict(uuid4(), uuid4())],
            "channel": [_channel_policy_dict(uuid4(), uuid4())],
            "row": [_row_policy_dict(uuid4(), 42, uuid4())],
        }

        def mock_get(*, route, **kw):
            assert route == "/policies"
            return fake

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.list_policies()
        assert set(result) == {"zone", "channel", "row"}
        assert result["zone"][0]["name"] == "Zone policy"
        assert isinstance(result["row"][0], dict)

    def test_list_policies_empty(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: {})
        result = rbac.list_policies()
        assert result == {"zone": [], "channel": [], "row": []}

    # --- zone ---
    def test_get_zone_policy_by_id_not_found(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", _raise_status(404))
        assert rbac.get_zone_policy_by_id(policy_id=uuid4()) is None

    def test_get_zone_policy_by_id_reraises(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", _raise_status(500))
        with pytest.raises(KronicleHTTPError):
            rbac.get_zone_policy_by_id(policy_id=uuid4())

    def test_get_zone_policy_by_id_found(self, rbac, monkeypatch):
        pid, zid = uuid4(), uuid4()
        fake = _zone_policy_dict(uuid4(), zid, id=str(pid))
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: fake)
        result = rbac.get_zone_policy_by_id(policy_id=pid)
        assert result is not None and str(result.id) == str(pid)

    def test_get_zone_policy_by_name(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: _zone_policy_dict(uuid4(), uuid4()))
        assert isinstance(rbac.get_zone_policy_by_name("Zone policy"), KronicleZonePolicy)

    def test_get_zone_policy_by_name_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: None)
        assert rbac.get_zone_policy_by_name("Ghost") is None

    def test_get_zone_policy_id_branch(self, rbac, monkeypatch):
        pid = uuid4()
        existing = _zone_policy_obj(uuid4(), uuid4(), policy_id=pid)
        monkeypatch.setattr(rbac, "get_zone_policy_by_id", lambda **kw: existing)
        assert rbac.get_zone_policy(_zone_policy_obj(uuid4(), uuid4(), policy_id=pid)) is existing

    def test_get_zone_policy_name_branch(self, rbac, monkeypatch):
        existing = _zone_policy_obj(uuid4(), uuid4(), name="Named")
        monkeypatch.setattr(rbac, "get_zone_policy_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_zone_policy_by_name", lambda **kw: existing)
        assert rbac.get_zone_policy(_zone_policy_obj(uuid4(), uuid4(), name="Named")) is existing

    def test_get_zone_policy_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get_zone_policy_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_zone_policy_by_name", lambda **kw: None)
        monkeypatch.setattr(rbac, "list_zone_policies", lambda: [])
        assert rbac.get_zone_policy(_zone_policy_obj(uuid4(), uuid4())) is None

    def test_patch_zone_policy(self, rbac, monkeypatch):
        pid, zid = uuid4(), uuid4()

        def mock_patch(*, route, body, **kw):
            assert str(pid) in route
            return _zone_policy_dict(uuid4(), zid, id=str(pid))

        monkeypatch.setattr(rbac, "patch", mock_patch)
        policy = _zone_policy_obj(uuid4(), zid, policy_id=pid)
        assert isinstance(rbac.patch_zone_policy(policy), KronicleZonePolicy)

    # --- channel ---
    def test_get_channel_policy_by_id_not_found(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", _raise_status(404))
        assert rbac.get_channel_policy_by_id(policy_id=uuid4()) is None

    def test_get_channel_policy_by_id_reraises(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", _raise_status(500))
        with pytest.raises(KronicleHTTPError):
            rbac.get_channel_policy_by_id(policy_id=uuid4())

    def test_get_channel_policy_by_id_found(self, rbac, monkeypatch):
        pid, cid = uuid4(), uuid4()
        fake = _channel_policy_dict(uuid4(), cid, id=str(pid))
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: fake)
        result = rbac.get_channel_policy_by_id(policy_id=pid)
        assert result is not None and str(result.id) == str(pid)

    def test_get_channel_policy_by_name(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: _channel_policy_dict(uuid4(), uuid4()))
        assert isinstance(rbac.get_channel_policy_by_name("Channel policy"), KronicleChannelPolicy)

    def test_get_channel_policy_by_name_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: None)
        assert rbac.get_channel_policy_by_name("Ghost") is None

    def test_get_channel_policy_id_branch(self, rbac, monkeypatch):
        pid = uuid4()
        existing = _channel_policy_obj(uuid4(), uuid4(), policy_id=pid)
        monkeypatch.setattr(rbac, "get_channel_policy_by_id", lambda **kw: existing)
        assert rbac.get_channel_policy(_channel_policy_obj(uuid4(), uuid4(), policy_id=pid)) is existing

    def test_get_channel_policy_name_branch(self, rbac, monkeypatch):
        existing = _channel_policy_obj(uuid4(), uuid4(), name="Named")
        monkeypatch.setattr(rbac, "get_channel_policy_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_channel_policy_by_name", lambda **kw: existing)
        assert rbac.get_channel_policy(_channel_policy_obj(uuid4(), uuid4(), name="Named")) is existing

    def test_get_channel_policy_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get_channel_policy_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_channel_policy_by_name", lambda **kw: None)
        monkeypatch.setattr(rbac, "list_channel_policies", lambda: [])
        assert rbac.get_channel_policy(_channel_policy_obj(uuid4(), uuid4())) is None

    def test_patch_channel_policy(self, rbac, monkeypatch):
        pid, cid = uuid4(), uuid4()

        def mock_patch(*, route, body, **kw):
            assert str(pid) in route
            return _channel_policy_dict(uuid4(), cid, id=str(pid))

        monkeypatch.setattr(rbac, "patch", mock_patch)
        policy = _channel_policy_obj(uuid4(), cid, policy_id=pid)
        assert isinstance(rbac.patch_channel_policy(policy), KronicleChannelPolicy)

    # --- row ---
    def test_get_row_policy_by_id_not_found(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", _raise_status(404))
        assert rbac.get_row_policy_by_id(policy_id=uuid4()) is None

    def test_get_row_policy_by_id_reraises(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", _raise_status(500))
        with pytest.raises(KronicleHTTPError):
            rbac.get_row_policy_by_id(policy_id=uuid4())

    def test_get_row_policy_by_id_found(self, rbac, monkeypatch):
        pid, cid = uuid4(), uuid4()
        fake = _row_policy_dict(uuid4(), 42, cid, id=str(pid))
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: fake)
        result = rbac.get_row_policy_by_id(policy_id=pid)
        assert result is not None and str(result.id) == str(pid)

    def test_get_row_policy_by_name(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: _row_policy_dict(uuid4(), 42, uuid4()))
        assert isinstance(rbac.get_row_policy_by_name("Row policy"), KronicleRowPolicy)

    def test_get_row_policy_by_name_none(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda *, route, **kw: None)
        assert rbac.get_row_policy_by_name("Ghost") is None

    def test_get_row_policy_id_branch(self, rbac, monkeypatch):
        cid, pid = uuid4(), uuid4()
        existing = _row_policy_obj(uuid4(), 42, cid, policy_id=pid)
        monkeypatch.setattr(rbac, "get_row_policy_by_id", lambda **kw: existing)
        assert rbac.get_row_policy(_row_policy_obj(uuid4(), 42, cid, policy_id=pid)) is existing

    def test_get_row_policy_name_branch(self, rbac, monkeypatch):
        cid = uuid4()
        existing = _row_policy_obj(uuid4(), 42, cid, name="Named")
        monkeypatch.setattr(rbac, "get_row_policy_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_row_policy_by_name", lambda **kw: existing)
        assert rbac.get_row_policy(_row_policy_obj(uuid4(), 42, cid, name="Named")) is existing

    def test_get_row_policy_none(self, rbac, monkeypatch):
        cid = uuid4()
        monkeypatch.setattr(rbac, "get_row_policy_by_id", lambda **kw: None)
        monkeypatch.setattr(rbac, "get_row_policy_by_name", lambda **kw: None)
        monkeypatch.setattr(rbac, "list_row_policies", lambda: [])
        assert rbac.get_row_policy(_row_policy_obj(uuid4(), 42, cid)) is None

    def test_patch_row_policy(self, rbac, monkeypatch):
        pid, cid = uuid4(), uuid4()

        def mock_patch(*, route, body, **kw):
            assert str(pid) in route
            return _row_policy_dict(uuid4(), 42, cid, id=str(pid))

        monkeypatch.setattr(rbac, "patch", mock_patch)
        policy = _row_policy_obj(uuid4(), 42, cid, policy_id=pid)
        assert isinstance(rbac.patch_row_policy(policy), KronicleRowPolicy)
