# tests/connectors/test_channel_writer.py
from uuid import uuid4

import pytest

from kronicle_sdk.connectors.channel.channel_writer import KronicleWriter
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.kronicle_errors import KronicleOperationError
from kronicle_sdk.models.rbac.kronicle_zone import KronicleZone


def channel_dict(cid, name="Channel_1"):
    return {"id": str(cid), "name": name}


@pytest.fixture
def writer():
    return KronicleWriter(url="http://localhost:8765", usr="admin", pwd="secret")


class TestKronicleWriterBasics:
    def test_prefix(self, writer):
        assert writer.prefix == "/data/v1"


class TestCreateChannel:
    def test_zone_from_payload(self, writer, monkeypatch):
        zid = uuid4()
        payload = KronicleChannel(name="Channel_1", zone=KronicleZone(id=zid))
        captured = {}

        def mock_post(*, route, body, **kw):
            captured["route"] = route
            return channel_dict(payload.id)

        monkeypatch.setattr(writer, "get_channel", lambda c: None)
        monkeypatch.setattr(writer, "post", mock_post)
        out = writer.create_channel(payload)
        assert captured["route"] == f"zones/{zid}/channels"
        assert isinstance(out, KronicleChannel)

    def test_explicit_zone_id(self, writer, monkeypatch):
        zid = uuid4()
        cid = uuid4()
        captured = {}

        def mock_post(*, route, body, **kw):
            captured["route"] = route
            return channel_dict(cid)

        monkeypatch.setattr(writer, "get_channel", lambda c: None)
        monkeypatch.setattr(writer, "post", mock_post)
        out = writer.create_channel(KronicleChannel(id=cid, name="Channel_1"), zone_id=zid)
        assert captured["route"] == f"zones/{zid}/channels"
        assert isinstance(out, KronicleChannel)

    def test_missing_zone_raises(self, writer):
        with pytest.raises(ValueError):
            writer.create_channel(KronicleChannel(name="Channel_1"))

    def test_existing_same_zone_returned(self, writer, monkeypatch):
        zid = uuid4()
        existing = KronicleChannel(name="Channel_1", zone=KronicleZone(id=zid))
        monkeypatch.setattr(writer, "get_channel", lambda c: existing)
        monkeypatch.setattr(writer, "post", lambda **kw: pytest.fail("post should not be called"))
        assert writer.create_channel(KronicleChannel(name="Channel_1"), zone_id=zid) is existing

    def test_existing_other_zone_raises(self, writer, monkeypatch):
        zid = uuid4()
        other = uuid4()
        existing = KronicleChannel(name="Channel_1", zone=KronicleZone(id=other))
        monkeypatch.setattr(writer, "get_channel", lambda c: existing)
        with pytest.raises(KronicleOperationError):
            writer.create_channel(KronicleChannel(name="Channel_1"), zone_id=zid)

    def test_existing_unknown_zone_raises(self, writer, monkeypatch):
        zid = uuid4()
        existing = KronicleChannel(name="Channel_1")  # no zone
        monkeypatch.setattr(writer, "get_channel", lambda c: existing)
        with pytest.raises(KronicleOperationError, match="unknown"):
            writer.create_channel(KronicleChannel(name="Channel_1"), zone_id=zid)


class TestPatchChannel:
    def test_patch_channel_dispatches_body(self, writer, monkeypatch):
        cid = uuid4()
        captured = {}

        def mock_patch(*, route, body, **kw):
            captured["route"] = route
            captured["body"] = body
            return channel_dict(cid)

        monkeypatch.setattr(writer, "patch", mock_patch)
        out = writer.patch_channel(KronicleChannel(id=cid, name="Channel_1"))
        assert captured["route"] == f"channels/{cid}"
        assert captured["body"].name == "Channel_1"
        assert "zone" not in writer._serialize_payload(captured["body"])
        assert isinstance(out, KronicleChannel)


class TestInsertRows:
    def test_insert_rows_and_update_channel(self, writer, monkeypatch):
        cid = uuid4()
        captured = {}

        def mock_post(*, route, body, **kw):
            captured["route"] = route
            return channel_dict(cid)

        monkeypatch.setattr(writer, "post", mock_post)
        out = writer.insert_rows_and_update_channel(KronicleChannel(id=cid, name="Channel_1", rows=[{"a": 1}]))
        assert captured["route"] == f"channels/{cid}"
        assert isinstance(out, KronicleChannel)

    def test_insert_rows_and_update_channel_from_dict(self, writer, monkeypatch):
        cid = uuid4()
        monkeypatch.setattr(writer, "post", lambda *, route, body, **kw: channel_dict(cid))
        out = writer.insert_rows_and_update_channel({"id": str(cid), "name": "Channel_1"})
        assert isinstance(out, KronicleChannel)

    def test_insert_rows(self, writer, monkeypatch):
        cid = uuid4()
        captured = {}

        def mock_post(route, body=None, **kw):
            captured["route"] = route
            captured["body"] = body
            return channel_dict(cid)

        monkeypatch.setattr(writer, "post", mock_post)
        out = writer.insert_rows(cid, [{"a": 1}])
        assert captured["route"] == f"channels/{cid}/rows"
        assert captured["body"].rows == [{"a": 1}]
        assert isinstance(out, KronicleChannel)
