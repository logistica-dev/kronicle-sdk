# tests/connectors/test_rbac_policy_methods.py
from uuid import uuid4

import pytest

from kronicle_sdk.connectors.rbac.rbac_setup import KronicleRbac
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.rbac.kronicle_access_profile import (
    KronicleChannelAccess,
    KronicleZoneAccess,
)
from kronicle_sdk.models.rbac.kronicle_policy import (
    KronicleChannelPolicy,
    KronicleZonePolicy,
)
from kronicle_sdk.models.rbac.kronicle_role import KronicleRole
from kronicle_sdk.models.rbac.kronicle_zone import KronicleZone


@pytest.fixture
def rbac():
    return KronicleRbac(url="http://localhost:8765", usr="admin", pwd="secret")


def _zone_access_dict(role_id, zone_id, description=None):
    return {
        "id": str(uuid4()),
        "name": "Zone acc",
        "details": None,
        "description": description,
        "role": {
            "id": str(role_id),
            "name": "Reader",
            "details": {},
            "description": "",
            "permissions": ["data:access"],
        },
        "zone": {"id": str(zone_id), "name": "ZoneA", "details": {"init": True}},
    }


def _channel_access_dict(role_id, channel_id, description=None):
    return {
        "id": str(uuid4()),
        "name": "Channel acc",
        "details": None,
        "description": description,
        "role": {
            "id": str(role_id),
            "name": "Writer",
            "details": {},
            "description": "",
            "permissions": ["data:access"],
        },
        "channel": {"id": str(channel_id), "name": "Channel_1", "details": None},
    }


def _zone_policy_dict(role_id, zone_id):
    return {
        "id": str(uuid4()),
        "name": "Zone policy",
        "details": None,
        "description": None,
        "is_delegation": False,
        "delegation_start": None,
        "delegation_end": None,
        "subject": {"id": str(uuid4()), "name": "scoped", "details": None, "type": "group", "group_id": str(uuid4())},
        "access_profile": _zone_access_dict(role_id, zone_id),
    }


def _channel_policy_dict(role_id, channel_id):
    return {
        "id": str(uuid4()),
        "name": "Channel policy",
        "details": None,
        "description": None,
        "is_delegation": False,
        "delegation_start": None,
        "delegation_end": None,
        "subject": {"id": str(uuid4()), "name": "scoped", "details": None, "type": "group", "group_id": str(uuid4())},
        "access_profile": _channel_access_dict(role_id, channel_id),
    }


class TestKronicleRbacZoneAccessProfiles:
    def test_create(self, rbac, monkeypatch):
        rid, zid = uuid4(), uuid4()
        fake = _zone_access_dict(rid, zid, description="test desc")

        def mock_post(*, route, body, **kw):
            assert route == "/access-profiles/zones"
            assert body["role"]["id"] == str(rid)
            assert body["zone"]["id"] == str(zid)
            assert body["description"] == "test desc"
            return fake

        monkeypatch.setattr(rbac, "post", mock_post)
        access = KronicleZoneAccess(
            role=KronicleRole(id=rid, name="Reader", permissions=["data:access"]),
            zone=KronicleZone(id=zid, name="ZoneA"),
            description="test desc",
        )
        result = rbac.create_zone_access_profile(access)
        assert isinstance(result, KronicleZoneAccess)
        assert result.zone.id == zid

    def test_create_with_description(self, rbac, monkeypatch):
        rid, zid = uuid4(), uuid4()
        fake = _zone_access_dict(rid, zid, description="test desc")

        def mock_post(*, route, body, **kw):
            assert body["description"] == "test desc"
            return fake

        monkeypatch.setattr(rbac, "post", mock_post)
        access = KronicleZoneAccess(
            role=KronicleRole(id=rid, name="Reader"),
            zone=KronicleZone(id=zid, name="ZoneA"),
            description="test desc",
        )
        result = rbac.create_zone_access_profile(access)
        assert result.description == "test desc"

    def test_list(self, rbac, monkeypatch):
        fake = [_zone_access_dict(uuid4(), uuid4())]

        def mock_get(*, route, **kw):
            assert route == "/access-profiles/zones"
            return fake

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.list_zone_access_profiles()
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], KronicleZoneAccess)

    def test_get_found(self, rbac, monkeypatch):
        pid, zid = uuid4(), uuid4()
        fake = _zone_access_dict(uuid4(), zid)

        def mock_get(*, route, **kw):
            assert str(pid) in route
            return fake

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.get_zone_access_profile(profile_id=pid)
        assert isinstance(result, KronicleZoneAccess)
        assert str(result.id) == fake["id"]

    def test_delete(self, rbac, monkeypatch):
        pid = uuid4()
        fake = _zone_access_dict(uuid4(), uuid4())

        def mock_delete(*, route, **kw):
            assert str(pid) in route
            return fake

        monkeypatch.setattr(rbac, "delete", mock_delete)
        result = rbac.delete_zone_access_profile(profile_id=pid)
        assert isinstance(result, KronicleZoneAccess)
        assert str(result.id) == fake["id"]


class TestKronicleRbacChannelAccessProfiles:
    def test_create(self, rbac, monkeypatch):
        rid, cid = uuid4(), uuid4()
        fake = _channel_access_dict(rid, cid)

        def mock_post(*, route, body, **kw):
            assert route == "/access-profiles/channels"
            assert body["role"]["id"] == str(rid)
            assert body["channel"]["id"] == str(cid)
            return fake

        monkeypatch.setattr(rbac, "post", mock_post)
        access = KronicleChannelAccess(
            role=KronicleRole(id=rid, name="Writer"),
            channel=KronicleChannel(id=cid, name="Channel_1"),
        )
        result = rbac.create_channel_access_profile(access)
        assert isinstance(result, KronicleChannelAccess)
        assert result.channel.id == cid

    def test_list(self, rbac, monkeypatch):
        fake = [_channel_access_dict(uuid4(), uuid4())]

        def mock_get(*, route, **kw):
            assert route == "/access-profiles/channels"
            return fake

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.list_channel_access_profiles()
        assert len(result) == 1
        assert isinstance(result[0], KronicleChannelAccess)

    def test_get_found(self, rbac, monkeypatch):
        pid, cid = uuid4(), uuid4()
        fake = _channel_access_dict(uuid4(), cid)

        def mock_get(*, route, **kw):
            assert str(pid) in route
            return fake

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.get_channel_access_profile(profile_id=pid)
        assert isinstance(result, KronicleChannelAccess)
        assert str(result.id) == fake["id"]

    def test_delete(self, rbac, monkeypatch):
        pid = uuid4()
        fake = _channel_access_dict(uuid4(), uuid4())

        def mock_delete(*, route, **kw):
            assert str(pid) in route
            return fake

        monkeypatch.setattr(rbac, "delete", mock_delete)
        result = rbac.delete_channel_access_profile(profile_id=pid)
        assert isinstance(result, KronicleChannelAccess)


class TestKronicleRbacZonePolicies:
    def test_create(self, rbac, monkeypatch):
        sid, rid, zid = uuid4(), uuid4(), uuid4()
        fake = _zone_policy_dict(rid, zid)

        def mock_post(*, route, body, **kw):
            assert route == "/policies/zones"
            return fake

        monkeypatch.setattr(rbac, "post", mock_post)
        from kronicle_sdk.models.rbac.kronicle_policy import KronicleSubject

        policy = KronicleZonePolicy(
            subject=KronicleSubject(type="group", name="scoped", group_id=sid),
            access_profile=KronicleZoneAccess(
                role=KronicleRole(id=rid, name="Reader"),
                zone=KronicleZone(id=zid, name="ZoneA"),
            ),
        )
        result = rbac.create_zone_policy(policy)
        assert isinstance(result, KronicleZonePolicy)
        assert str(result.id) == fake["id"]

    def test_list(self, rbac, monkeypatch):
        fake = [_zone_policy_dict(uuid4(), uuid4())]

        def mock_get(*, route, **kw):
            assert route == "/policies/zones"
            return fake

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.list_zone_policies()
        assert len(result) == 1
        assert isinstance(result[0], KronicleZonePolicy)

    def test_delete(self, rbac, monkeypatch):
        pid = uuid4()
        fake = _zone_policy_dict(uuid4(), uuid4())

        def mock_delete(*, route, **kw):
            assert str(pid) in route
            return fake

        monkeypatch.setattr(rbac, "delete", mock_delete)
        result = rbac.delete_zone_policy(policy_id=pid)
        assert isinstance(result, KronicleZonePolicy)


class TestKronicleRbacChannelPolicies:
    def test_create(self, rbac, monkeypatch):
        sid, rid, cid = uuid4(), uuid4(), uuid4()
        fake = _channel_policy_dict(rid, cid)

        def mock_post(*, route, body, **kw):
            assert route == "/policies/channels"
            return fake

        monkeypatch.setattr(rbac, "post", mock_post)
        from kronicle_sdk.models.rbac.kronicle_policy import KronicleSubject

        policy = KronicleChannelPolicy(
            subject=KronicleSubject(type="group", name="scoped", group_id=sid),
            access_profile=KronicleChannelAccess(
                role=KronicleRole(id=rid, name="Writer"),
                channel=KronicleChannel(id=cid, name="Channel_1"),
            ),
        )
        result = rbac.create_channel_policy(policy)
        assert isinstance(result, KronicleChannelPolicy)
        assert str(result.id) == fake["id"]

    def test_list(self, rbac, monkeypatch):
        fake = [_channel_policy_dict(uuid4(), uuid4())]

        def mock_get(*, route, **kw):
            assert route == "/policies/channels"
            return fake

        monkeypatch.setattr(rbac, "get", mock_get)
        result = rbac.list_channel_policies()
        assert len(result) == 1
        assert isinstance(result[0], KronicleChannelPolicy)

    def test_delete(self, rbac, monkeypatch):
        pid = uuid4()
        fake = _channel_policy_dict(uuid4(), uuid4())

        def mock_delete(*, route, **kw):
            assert str(pid) in route
            return fake

        monkeypatch.setattr(rbac, "delete", mock_delete)
        result = rbac.delete_channel_policy(policy_id=pid)
        assert isinstance(result, KronicleChannelPolicy)
