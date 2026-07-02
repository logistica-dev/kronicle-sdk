from uuid import uuid4

import pytest

from kronicle_sdk.connectors.rbac.rbac_setup import KronicleRbac
from kronicle_sdk.models.rbac.kronicle_role import KronicleRole


@pytest.fixture
def rbac():
    return KronicleRbac(url="http://localhost:8765", usr="admin", pwd="secret")


class TestKronicleRbacRoles:
    def test_list_roles(self, rbac, monkeypatch):
        fake_roles = [
            {"id": str(uuid4()), "name": "reader", "permissions": ["channel:read"]},
            {"id": str(uuid4()), "name": "writer", "permissions": ["channel:write"]},
        ]

        def mock_get(*, route, **kw):
            return fake_roles

        monkeypatch.setattr(rbac, "get", mock_get)
        roles = rbac.list_roles()
        assert len(roles) == 2
        assert all(isinstance(r, KronicleRole) for r in roles)
        assert roles[0].name == "reader"

    def test_get_role_by_id_found(self, rbac, monkeypatch):
        rid = uuid4()
        fake = {"id": str(rid), "name": "admin", "permissions": ["rbac:manage"]}

        def mock_get(*, route, **kw):
            return fake

        monkeypatch.setattr(rbac, "get", mock_get)
        role = rbac.get_role_by_id(role_id=rid)
        assert role is not None
        assert role.name == "admin"

    def test_get_role_by_id_not_found(self, rbac, monkeypatch):
        def mock_get(*, route, **kw):
            return None

        monkeypatch.setattr(rbac, "get", mock_get)
        role = rbac.get_role_by_id(role_id=uuid4())
        assert role is None

    def test_get_role_by_name_found(self, rbac, monkeypatch):
        fake = {"id": str(uuid4()), "name": "viewer", "permissions": ["channel:read"]}

        def mock_get(*, route, **kw):
            return fake

        monkeypatch.setattr(rbac, "get", mock_get)
        role = rbac.get_role_by_name(name="viewer")
        assert role is not None
        assert role.name == "viewer"

    def test_get_role_by_name_not_found(self, rbac, monkeypatch):
        def mock_get(*, route, **kw):
            return None

        monkeypatch.setattr(rbac, "get", mock_get)
        role = rbac.get_role_by_name(name="nonexistent")
        assert role is None

    def test_create_role(self, rbac, monkeypatch):
        rid = uuid4()
        fake = {"id": str(rid), "name": "editor", "permissions": ["channel:write"]}

        def mock_post(*, route, body, **kw):
            assert body["name"] == "editor"
            return fake

        monkeypatch.setattr(rbac, "post", mock_post)
        role = rbac.create_role(KronicleRole(name="editor", permissions=["channel:write"]))
        assert role.name == "editor"
        assert role.id == rid

    def test_patch_role(self, rbac, monkeypatch):
        rid = uuid4()
        fake = {"id": str(rid), "name": "updated", "permissions": ["channel:read"]}

        def mock_patch(*, route, body, **kw):
            assert body["name"] == "updated"
            return fake

        monkeypatch.setattr(rbac, "patch", mock_patch)
        role = rbac.patch_role(role_id=rid, role=KronicleRole(name="updated"))
        assert role.name == "updated"

    def test_delete_role(self, rbac, monkeypatch):
        rid = uuid4()
        fake = {"id": str(rid), "name": "deleted", "permissions": []}

        def mock_delete(*, route, **kw):
            return fake

        monkeypatch.setattr(rbac, "delete", mock_delete)
        role = rbac.delete_role(role_id=rid)
        assert role is not None
        assert role.name == "deleted"

    def test_delete_role_not_found(self, rbac, monkeypatch):
        def mock_delete(*, route, **kw):
            return None

        monkeypatch.setattr(rbac, "delete", mock_delete)
        role = rbac.delete_role(role_id=uuid4())
        assert role is None

    def test_assign_role_to_user(self, rbac, monkeypatch):
        rid = uuid4()
        uid = uuid4()

        def mock_put(*, route, **kw):
            assert str(rid) in route
            assert str(uid) in route
            return {"detail": "assigned"}

        monkeypatch.setattr(rbac, "put", mock_put)
        result = rbac.assign_role_to_user(role_id=rid, user_id=uid)
        assert result["detail"] == "assigned"

    def test_assign_role_to_group(self, rbac, monkeypatch):
        rid = uuid4()
        gid = uuid4()

        def mock_put(*, route, **kw):
            assert str(rid) in route
            assert str(gid) in route
            return {"detail": "assigned"}

        monkeypatch.setattr(rbac, "put", mock_put)
        result = rbac.assign_role_to_group(role_id=rid, group_id=gid)
        assert result["detail"] == "assigned"

    def test_remove_role_from_user(self, rbac, monkeypatch):
        rid = uuid4()
        uid = uuid4()

        def mock_delete(*, route, **kw):
            assert str(rid) in route
            assert str(uid) in route
            return {"detail": "removed"}

        monkeypatch.setattr(rbac, "delete", mock_delete)
        result = rbac.remove_role_from_user(role_id=rid, user_id=uid)
        assert result["detail"] == "removed"

    def test_remove_role_from_group(self, rbac, monkeypatch):
        rid = uuid4()
        gid = uuid4()

        def mock_delete(*, route, **kw):
            assert str(rid) in route
            assert str(gid) in route
            return {"detail": "removed"}

        monkeypatch.setattr(rbac, "delete", mock_delete)
        result = rbac.remove_role_from_group(role_id=rid, group_id=gid)
        assert result["detail"] == "removed"

    def test_check_user_has_role_direct(self, rbac, monkeypatch):
        uid = uuid4()
        rid = uuid4()

        def mock_get(*, route, **kw):
            assert str(uid) in route
            assert str(rid) in route
            return {"has_role": True, "direct": True}

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.check_user_has_role(user_id=uid, role_id=rid)
        assert result["has_role"] is True
        assert result["direct"] is True

    def test_check_user_has_role_indirect(self, rbac, monkeypatch):
        uid = uuid4()
        rid = uuid4()

        def mock_get(*, route, **kw):
            assert str(uid) in route
            assert str(rid) in route
            assert kw.get("params") == {"indirect": "1"}
            return {"has_role": True, "direct": False}

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.check_user_has_role(user_id=uid, role_id=rid, indirect=True)
        assert result["has_role"] is True
        assert result["direct"] is False

    def test_check_group_has_role_direct(self, rbac, monkeypatch):
        gid = uuid4()
        rid = uuid4()

        def mock_get(*, route, **kw):
            assert str(gid) in route
            assert str(rid) in route
            return {"has_role": True, "direct": True}

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.check_group_has_role(group_id=gid, role_id=rid)
        assert result["has_role"] is True
        assert result["direct"] is True

    def test_check_group_has_role_indirect(self, rbac, monkeypatch):
        gid = uuid4()
        rid = uuid4()

        def mock_get(*, route, **kw):
            assert str(gid) in route
            assert str(rid) in route
            assert kw.get("params") == {"indirect": "1"}
            return {"has_role": True, "direct": False}

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.check_group_has_role(group_id=gid, role_id=rid, indirect=True)
        assert result["has_role"] is True
        assert result["direct"] is False

    def test_list_role_subjects_direct(self, rbac, monkeypatch):
        rid = uuid4()

        def mock_get(*, route, **kw):
            assert str(rid) in route
            assert "subjects" in route
            return {"users": [], "groups": []}

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.list_role_subjects(role_id=rid)
        assert "users" in result
        assert "groups" in result

    def test_list_role_subjects_indirect(self, rbac, monkeypatch):
        rid = uuid4()

        def mock_get(*, route, **kw):
            assert str(rid) in route
            assert "subjects" in route
            assert kw.get("params") == {"indirect": "1"}
            return {"users": [], "groups": [], "indirect_users": []}

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.list_role_subjects(role_id=rid, indirect=True)
        assert "indirect_users" in result

    def test_get_users_for_role_direct(self, rbac, monkeypatch):
        rid = uuid4()

        def mock_list(*, role_id, indirect=False):
            assert role_id == rid
            assert indirect is False
            return {"users": ["u1", "u2"], "groups": ["g1"], "indirect_users": ["u3"]}

        monkeypatch.setattr(rbac, "list_role_subjects", mock_list)
        users = rbac.get_users_for_role(role_id=rid)
        assert users == ["u1", "u2"]

    def test_get_users_for_role_indirect(self, rbac, monkeypatch):
        rid = uuid4()

        def mock_list(*, role_id, indirect=False):
            assert indirect is True
            return {"users": ["u1"], "groups": [], "indirect_users": ["u2", "u3"]}

        monkeypatch.setattr(rbac, "list_role_subjects", mock_list)
        users = rbac.get_users_for_role(role_id=rid, indirect=True)
        assert users == ["u1", "u2", "u3"]

    def test_get_groups_for_role_direct(self, rbac, monkeypatch):
        rid = uuid4()

        def mock_list(*, role_id, indirect=False):
            return {"users": [], "groups": ["g1", "g2"], "indirect_users": []}

        monkeypatch.setattr(rbac, "list_role_subjects", mock_list)
        groups = rbac.get_groups_for_role(role_id=rid)
        assert groups == ["g1", "g2"]

    def test_get_groups_for_role_indirect(self, rbac, monkeypatch):
        rid = uuid4()

        def mock_list(*, role_id, indirect=False):
            assert indirect is True
            return {"users": [], "groups": ["g1"]}

        monkeypatch.setattr(rbac, "list_role_subjects", mock_list)
        groups = rbac.get_groups_for_role(role_id=rid, indirect=True)
        assert groups == ["g1"]

    def test_check_user_in_group_direct(self, rbac, monkeypatch):
        uid = uuid4()
        gid = uuid4()

        def mock_get(*, route, **kw):
            assert str(uid) in route
            assert str(gid) in route
            return {"is_member": True, "direct": True}

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.check_user_in_group(user_id=uid, group_id=gid)
        assert result["is_member"] is True
        assert result["direct"] is True

    def test_check_user_in_group_indirect(self, rbac, monkeypatch):
        uid = uuid4()
        gid = uuid4()

        def mock_get(*, route, **kw):
            assert str(uid) in route
            assert str(gid) in route
            assert kw.get("params") == {"indirect": "1"}
            return {"is_member": True, "direct": False}

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.check_user_in_group(user_id=uid, group_id=gid, indirect=True)
        assert result["is_member"] is True
        assert result["direct"] is False
