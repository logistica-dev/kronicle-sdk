from uuid import uuid4

import pytest

from kronicle_sdk.connectors.rbac.rbac_setup import KronicleRbac


@pytest.fixture
def rbac():
    return KronicleRbac(url="http://localhost:8765", usr="admin", pwd="secret")


class TestKronicleRbacZoneAccessProfiles:
    def test_create(self, rbac, monkeypatch):
        rid, zid = uuid4(), uuid4()
        fake = {
            "id": str(uuid4()),
            "role_id": str(rid),
            "zone_id": str(zid),
            "role_name": "Reader",
            "zone_name": "ZoneA",
            "description": None,
        }

        def mock_post(*, route, body, **kw):
            assert route == "/access-profiles/zones"
            assert body["role_id"] == str(rid)
            assert body["zone_id"] == str(zid)
            return fake

        monkeypatch.setattr(rbac, "post", mock_post)
        result = rbac.create_zone_access_profile(role_id=rid, zone_id=zid)
        assert result["role_id"] == str(rid)

    def test_create_with_description(self, rbac, monkeypatch):
        rid, zid = uuid4(), uuid4()

        def mock_post(*, route, body, **kw):
            assert body["description"] == "test desc"
            return {
                "id": str(uuid4()),
                "role_id": str(rid),
                "zone_id": str(zid),
                "role_name": "R",
                "zone_name": "Z",
                "description": "test desc",
            }

        monkeypatch.setattr(rbac, "post", mock_post)
        rbac.create_zone_access_profile(role_id=rid, zone_id=zid, description="test desc")

    def test_list(self, rbac, monkeypatch):
        fake = [
            {
                "id": str(uuid4()),
                "role_id": str(uuid4()),
                "zone_id": str(uuid4()),
                "role_name": "R",
                "zone_name": "Z",
                "description": None,
            }
        ]

        def mock_get(*, route, **kw):
            assert route == "/access-profiles/zones"
            return fake

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.list_zone_access_profiles()
        assert len(result) == 1

    def test_get_found(self, rbac, monkeypatch):
        pid = uuid4()
        fake = {
            "id": str(pid),
            "role_id": str(uuid4()),
            "zone_id": str(uuid4()),
            "role_name": "R",
            "zone_name": "Z",
            "description": None,
        }

        def mock_get(*, route, **kw):
            assert str(pid) in route
            return fake

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.get_zone_access_profile(profile_id=pid)
        assert result is not None

    def test_get_not_found(self, rbac, monkeypatch):
        def mock_get(*, route, **kw):
            return None

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.get_zone_access_profile(profile_id=uuid4())
        assert result is None

    def test_delete(self, rbac, monkeypatch):
        pid = uuid4()
        fake = {"detail": f"ZoneAccessProfile '{pid}' deleted"}

        def mock_delete(*, route, **kw):
            assert str(pid) in route
            return fake

        monkeypatch.setattr(rbac, "delete", mock_delete)
        result = rbac.delete_zone_access_profile(profile_id=pid)
        assert "deleted" in result["detail"]


class TestKronicleRbacChannelAccessProfiles:
    def test_create(self, rbac, monkeypatch):
        rid, cid = uuid4(), uuid4()

        def mock_post(*, route, body, **kw):
            assert route == "/access-profiles/channels"
            return {
                "id": str(uuid4()),
                "role_id": str(rid),
                "channel_id": str(cid),
                "role_name": "W",
                "channel_name": "Ch1",
                "description": None,
            }

        monkeypatch.setattr(rbac, "post", mock_post)
        rbac.create_channel_access_profile(role_id=rid, channel_id=cid)

    def test_list(self, rbac, monkeypatch):
        def mock_get(*, route, **kw):
            assert route == "/access-profiles/channels"
            return []

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.list_channel_access_profiles()
        assert result == []

    def test_get_found(self, rbac, monkeypatch):
        pid = uuid4()

        def mock_get(*, route, **kw):
            assert str(pid) in route
            return {
                "id": str(pid),
                "role_id": str(uuid4()),
                "channel_id": str(uuid4()),
                "role_name": "W",
                "channel_name": "Ch1",
                "description": None,
            }

        monkeypatch.setattr(rbac, "get", mock_get)
        assert rbac.get_channel_access_profile(profile_id=pid) is not None

    def test_get_not_found(self, rbac, monkeypatch):
        monkeypatch.setattr(rbac, "get", lambda **kw: None)
        assert rbac.get_channel_access_profile(profile_id=uuid4()) is None

    def test_delete(self, rbac, monkeypatch):
        pid = uuid4()
        monkeypatch.setattr(rbac, "delete", lambda **kw: {"detail": "deleted"})
        result = rbac.delete_channel_access_profile(profile_id=pid)
        assert "deleted" in result["detail"]


class TestKronicleRbacZonePolicies:
    def test_create(self, rbac, monkeypatch):
        sid, rid, zid = uuid4(), uuid4(), uuid4()

        def mock_post(*, route, body, **kw):
            assert route == "/policies/zones"
            return {
                "id": str(uuid4()),
                "subject_id": str(sid),
                "role_id": str(rid),
                "role_name": "R",
                "zone_id": str(zid),
                "is_delegation": False,
            }

        monkeypatch.setattr(rbac, "post", mock_post)
        result = rbac.create_zone_policy(subject_id=sid, role_id=rid, zone_id=zid)
        assert result["subject_id"] == str(sid)

    def test_list(self, rbac, monkeypatch):
        zid = uuid4()

        def mock_get(*, route, **kw):
            assert str(zid) in route
            return []

        monkeypatch.setattr(rbac, "get", mock_get)
        assert rbac.list_zone_policies(zone_id=zid) == []

    def test_delete(self, rbac, monkeypatch):
        pid = uuid4()
        monkeypatch.setattr(rbac, "delete", lambda **kw: {"detail": "deleted"})
        result = rbac.delete_zone_policy(policy_id=pid)
        assert "deleted" in result["detail"]


class TestKronicleRbacChannelPolicies:
    def test_create(self, rbac, monkeypatch):
        sid, rid, cid = uuid4(), uuid4(), uuid4()

        def mock_post(*, route, body, **kw):
            assert route == "/policies/channels"
            return {
                "id": str(uuid4()),
                "subject_id": str(sid),
                "role_id": str(rid),
                "channel_id": str(cid),
                "is_delegation": False,
            }

        monkeypatch.setattr(rbac, "post", mock_post)
        result = rbac.create_channel_policy(subject_id=sid, role_id=rid, channel_id=cid)
        assert result["channel_id"] == str(cid)

    def test_list(self, rbac, monkeypatch):
        cid = uuid4()
        monkeypatch.setattr(rbac, "get", lambda **kw: [])
        assert rbac.list_channel_policies(channel_id=cid) == []

    def test_delete(self, rbac, monkeypatch):
        pid = uuid4()
        monkeypatch.setattr(rbac, "delete", lambda **kw: {"detail": "deleted"})
        result = rbac.delete_channel_policy(policy_id=pid)
        assert "deleted" in result["detail"]
