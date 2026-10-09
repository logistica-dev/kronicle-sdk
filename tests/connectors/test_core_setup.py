# tests/connectors/test_core_setup.py
from uuid import uuid4

import pytest

from kronicle_sdk.connectors.rbac.core_setup import KronicleCore
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.kronicle_errors import KronicleHTTPError, KronicleHTTPErrorModel
from kronicle_sdk.models.rbac.kronicle_zone import KronicleZone


def zone_dict(zid=None, name="ZoneA", details=None):
    return {"id": str(zid or uuid4()), "name": name, "details": details}


def channel_dict(cid=None, name="Channel_1"):
    return {"id": str(cid or uuid4()), "name": name}


def http_error(status):
    return KronicleHTTPError(KronicleHTTPErrorModel(status=status, error="err", message="nope"))


@pytest.fixture
def core():
    return KronicleCore(url="http://localhost:8765", usr="admin", pwd="secret")


class TestKronicleCoreZones:
    def test_prefix(self, core):
        assert core.prefix == "/core/v1"

    def test_list_zones(self, core, monkeypatch):
        fake = [zone_dict(name="ZoneA"), zone_dict(name="ZoneB")]

        def mock_get(*, route, **kw):
            assert route == "/zones"
            return fake

        monkeypatch.setattr(core, "get", mock_get)
        zones = core.list_zones()
        assert len(zones) == 2
        assert all(isinstance(z, KronicleZone) for z in zones)
        assert zones[0].name == "ZoneA"

    def test_get_zone_by_id_found(self, core, monkeypatch):
        zid = uuid4()
        fake = zone_dict(zid=zid)

        def mock_get(*, route, **kw):
            assert str(zid) in route
            return fake

        monkeypatch.setattr(core, "get", mock_get)
        zone = core.get_zone_by_id(zid)
        assert zone is not None
        assert zone.id == zid

    def test_get_zone_by_id_not_found(self, core, monkeypatch):
        def mock_get(*, route, **kw):
            raise http_error(404)

        monkeypatch.setattr(core, "get", mock_get)
        assert core.get_zone_by_id(uuid4()) is None

    def test_get_zone_by_id_non_404_reraises(self, core, monkeypatch):
        def mock_get(*, route, **kw):
            raise http_error(500)

        monkeypatch.setattr(core, "get", mock_get)
        with pytest.raises(KronicleHTTPError):
            core.get_zone_by_id(uuid4())

    def test_get_zone_by_id_empty_body(self, core, monkeypatch):
        def mock_get(*, route, **kw):
            return None

        monkeypatch.setattr(core, "get", mock_get)
        assert core.get_zone_by_id(uuid4()) is None

    def test_get_zone_by_name_found(self, core, monkeypatch):
        fake = zone_dict(name="ZoneA")

        def mock_get(*, route, **kw):
            assert route == "/zones?name=ZoneA"
            return fake

        monkeypatch.setattr(core, "get", mock_get)
        zone = core.get_zone_by_name("ZoneA")
        assert zone is not None
        assert zone.name == "ZoneA"

    def test_get_zone_by_name_absent(self, core, monkeypatch):
        def mock_get(*, route, **kw):
            return None

        monkeypatch.setattr(core, "get", mock_get)
        assert core.get_zone_by_name("ZoneA") is None

    def test_get_zone_by_id_path(self, core, monkeypatch):
        zid = uuid4()

        def mock_get(*, route, **kw):
            assert str(zid) in route
            return zone_dict(zid=zid)

        monkeypatch.setattr(core, "get", mock_get)
        result = core.get_zone(KronicleZone(id=zid, name="ZoneA"))
        assert result is not None
        assert result.id == zid

    def test_get_zone_by_name_path(self, core, monkeypatch):
        zone = KronicleZone(name="ZoneA")
        zone.id = None

        def mock_get(*, route, **kw):
            assert route == "/zones?name=ZoneA"
            return zone_dict(name="ZoneA")

        monkeypatch.setattr(core, "get", mock_get)
        result = core.get_zone(zone)
        assert result is not None
        assert result.name == "ZoneA"

    def test_get_zone_none(self, core):
        zone = KronicleZone(name="ZoneA")
        zone.id = None
        zone.name = None
        assert core.get_zone(zone) is None

    def test_create_zone_returns_existing(self, core, monkeypatch):
        existing = KronicleZone(name="ZoneA")

        def mock_get_zone(zone):
            return existing

        def raise_post(*, route, body=None, **kw):
            raise AssertionError("post should not have been called")

        monkeypatch.setattr(core, "get_zone", mock_get_zone)
        monkeypatch.setattr(core, "post", raise_post)
        assert core.create_zone(KronicleZone(name="ZoneA")) is existing

    def test_create_zone_posts_and_parses(self, core, monkeypatch):
        zid = uuid4()

        def mock_get_zone(zone):
            return None

        def mock_post(*, route, body, **kw):
            assert route == "/zones"
            assert body["name"] == "ZoneA"
            return zone_dict(zid=zid, name="ZoneA")

        monkeypatch.setattr(core, "get_zone", mock_get_zone)
        monkeypatch.setattr(core, "post", mock_post)
        result = core.create_zone(KronicleZone(name="ZoneA"))
        assert result.id == zid

    def test_patch_zone_with_name_and_details(self, core, monkeypatch):
        zid = uuid4()
        captured = {}

        def mock_patch(*, route, body, **kw):
            captured["route"] = route
            captured["body"] = body
            return zone_dict(zid=zid, name="ZoneB")

        monkeypatch.setattr(core, "patch", mock_patch)
        core.patch_zone(KronicleZone(id=zid, name="ZoneB", details={"k": "v"}))
        assert captured["body"] == {"name": "ZoneB", "details": {"k": "v"}}

    def test_patch_zone_without_fields(self, core, monkeypatch):
        zid = uuid4()
        captured = {}

        def mock_patch(*, route, body, **kw):
            captured["body"] = body
            return zone_dict(zid=zid)

        monkeypatch.setattr(core, "patch", mock_patch)
        zone = KronicleZone(id=zid)
        zone.name = None
        zone.details = None
        core.patch_zone(zone)
        assert captured["body"] == {}

    def test_delete_zone_with_body(self, core, monkeypatch):
        zid = uuid4()

        def mock_delete(*, route, **kw):
            assert str(zid) in route
            return zone_dict(zid=zid)

        monkeypatch.setattr(core, "delete", mock_delete)
        result = core.delete_zone(zone_id=zid)
        assert result is not None
        assert result.id == zid

    def test_delete_zone_without_body(self, core, monkeypatch):
        def mock_delete(*, route, **kw):
            return None

        monkeypatch.setattr(core, "delete", mock_delete)
        assert core.delete_zone(zone_id=uuid4()) is None

    def test_delete_zone_by_name_missing(self, core, monkeypatch):
        def mock_get_zone_by_name(name):
            return None

        monkeypatch.setattr(core, "get_zone_by_name", mock_get_zone_by_name)
        assert core.delete_zone_by_name("ZoneA") is None

    def test_delete_zone_by_name_found(self, core, monkeypatch):
        zid = uuid4()

        def mock_get_zone_by_name(name):
            return KronicleZone(id=zid, name="ZoneA")

        def mock_delete(*, route, **kw):
            assert str(zid) in route
            return zone_dict(zid=zid)

        monkeypatch.setattr(core, "get_zone_by_name", mock_get_zone_by_name)
        monkeypatch.setattr(core, "delete", mock_delete)
        result = core.delete_zone_by_name("ZoneA")
        assert result is not None
        assert result.id == zid


class TestKronicleCoreChannels:
    def test_list_core_channels_all(self, core, monkeypatch):
        fake = [channel_dict(), channel_dict(name="Channel_2")]

        def mock_get(*, route, **kw):
            assert route == "/channels"
            return fake

        monkeypatch.setattr(core, "get", mock_get)
        channels = core.list_core_channels()
        assert len(channels) == 2
        assert all(isinstance(c, KronicleChannel) for c in channels)

    def test_list_core_channels_by_zone(self, core, monkeypatch):
        zid = uuid4()

        def mock_get(*, route, **kw):
            assert route == f"/zones/{zid}/channels"
            return [channel_dict()]

        monkeypatch.setattr(core, "get", mock_get)
        channels = core.list_core_channels(zone_id=zid)
        assert len(channels) == 1
        assert isinstance(channels[0], KronicleChannel)

    def test_get_core_channel_parses_payload(self, core, monkeypatch):
        cid = uuid4()

        def mock_get(*, route, **kw):
            assert route == f"/channels/{cid}"
            return channel_dict(cid=cid)

        monkeypatch.setattr(core, "get", mock_get)
        result = core.get_core_channel(channel_id=cid)
        assert isinstance(result, KronicleChannel)
        assert result.id == cid

    def test_get_core_channel_none_body_returns_none(self, core, monkeypatch):
        monkeypatch.setattr(core, "get", lambda *, route, **kw: None)
        assert core.get_core_channel(channel_id=uuid4()) is None

    def test_patch_core_channel_all_fields(self, core, monkeypatch):
        cid = uuid4()
        zid = uuid4()
        captured = {}

        def mock_patch(*, route, body, **kw):
            captured["route"] = route
            captured["body"] = body
            return channel_dict(cid=cid, name="Channel_2")

        monkeypatch.setattr(core, "patch", mock_patch)
        core.patch_core_channel(channel_id=cid, name="Channel_2", details={"a": 1}, zone_id=zid)
        assert captured["body"] == {"name": "Channel_2", "details": {"a": 1}, "zone_id": str(zid)}

    def test_patch_core_channel_without_fields(self, core, monkeypatch):
        cid = uuid4()
        captured = {}

        def mock_patch(*, route, body, **kw):
            captured["body"] = body
            return channel_dict(cid=cid)

        monkeypatch.setattr(core, "patch", mock_patch)
        core.patch_core_channel(channel_id=cid)
        assert captured["body"] == {}

    def test_change_channel_zone(self, core, monkeypatch):
        cid = uuid4()
        zid = uuid4()
        captured = {}

        def mock_patch(*, route, body, **kw):
            captured["route"] = route
            captured["body"] = body
            return channel_dict(cid=cid)

        monkeypatch.setattr(core, "patch", mock_patch)
        result = core.change_channel_zone(channel_id=cid, zone_id=zid)
        assert captured["route"] == f"/channels/{cid}"
        assert captured["body"] == {"zone_id": str(zid)}
        assert isinstance(result, KronicleChannel)

    def test_delete_core_channel(self, core, monkeypatch):
        cid = uuid4()

        def mock_delete(*, route, **kw):
            assert str(cid) in route
            return channel_dict(cid=cid)

        monkeypatch.setattr(core, "delete", mock_delete)
        result = core.delete_core_channel(cid)
        assert isinstance(result, KronicleChannel)
        assert result.id == cid

    def test_sync_core_channels(self, core, monkeypatch):
        def mock_post(*, route, **kw):
            assert route == "/sync"
            return {"synced": 2}

        monkeypatch.setattr(core, "post", mock_post)
        assert core.sync_core_channels() == {"synced": 2}
