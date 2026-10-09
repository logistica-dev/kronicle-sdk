# tests/connectors/test_channel_setup.py
from uuid import uuid4

import pytest

from kronicle_sdk.connectors.channel.channel_setup import KronicleSetup
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.kronicle_errors import KronicleOperationError


def channel_dict(cid, name="Channel_1"):
    return {"id": str(cid), "name": name}


@pytest.fixture
def setup():
    return KronicleSetup(url="http://localhost:8765", usr="admin", pwd="secret")


class TestKronicleSetupBasics:
    def test_prefix(self, setup):
        assert setup.prefix == "/setup/v1"

    def test_column_types(self, setup, monkeypatch):
        captured = {}

        def mock_get(*, route, strict=True, **kw):
            captured["route"] = route
            captured["strict"] = strict
            return {"value": "float"}

        monkeypatch.setattr(setup, "get", mock_get)
        assert setup.column_types == {"value": "float"}
        assert captured["strict"] is False
        assert captured["route"] == "schemas/column_types"


class TestUpsertUpdateDelete:
    def test_upsert_channel(self, setup, monkeypatch):
        cid = uuid4()
        captured = {}

        def mock_put(*, route, body, **kw):
            captured["route"] = route
            return channel_dict(cid)

        monkeypatch.setattr(setup, "put", mock_put)
        out = setup.upsert_channel(KronicleChannel(id=cid, name="Channel_1"))
        assert captured["route"] == "channels"
        assert isinstance(out, KronicleChannel)

    def test_upsert_channel_from_dict(self, setup, monkeypatch):
        cid = uuid4()
        monkeypatch.setattr(setup, "put", lambda *, route, body, **kw: channel_dict(cid))
        out = setup.upsert_channel({"id": str(cid), "name": "Channel_1"})
        assert isinstance(out, KronicleChannel)

    def test_update_channel(self, setup, monkeypatch):
        cid = uuid4()
        captured = {}

        def mock_patch(*, route, body, **kw):
            captured["route"] = route
            return channel_dict(cid)

        monkeypatch.setattr(setup, "patch", mock_patch)
        out = setup.update_channel(KronicleChannel(id=cid, name="Channel_1"))
        assert captured["route"] == f"channels/{cid}"
        assert isinstance(out, KronicleChannel)

    def test_delete_channel_found(self, setup, monkeypatch):
        cid = uuid4()
        channel = KronicleChannel(id=cid, name="Channel_1")
        captured = {}

        def mock_delete(*, route, **kw):
            captured["route"] = route
            return channel_dict(cid)

        monkeypatch.setattr(setup, "get_channel_by_id", lambda id: channel)
        monkeypatch.setattr(setup, "delete", mock_delete)
        out = setup.delete_channel(cid)
        assert captured["route"] == f"channels/{cid}"
        assert isinstance(out, KronicleChannel)

    def test_delete_channel_not_found(self, setup, monkeypatch):
        monkeypatch.setattr(setup, "get_channel_by_id", lambda id: None)
        with pytest.raises(KronicleOperationError):
            setup.delete_channel(uuid4())

    def test_delete_all_channels_continues_after_error(self, setup, monkeypatch):
        id1 = uuid4()
        id2 = uuid4()
        setup._metadata_cache = [
            KronicleChannel(id=id1, name="Channel_1"),
            KronicleChannel(id=id2, name="Channel_2"),
        ]
        seen = []

        def mock_delete_channel(channel_id):
            seen.append(channel_id)
            if channel_id == id1:
                raise RuntimeError("boom")
            return KronicleChannel(id=channel_id, name="Channel_2")

        monkeypatch.setattr(setup, "delete_channel", mock_delete_channel)
        setup.delete_all_channels()
        assert seen == [id1, id2]


class TestCloneChannel:
    def test_str_id_no_body(self, setup, monkeypatch):
        cid = uuid4()
        captured = {}

        def mock_post(*, route, body, **kw):
            captured["route"] = route
            captured["body"] = body
            return channel_dict(cid)

        monkeypatch.setattr(setup, "post", mock_post)
        out = setup.clone_channel(str(cid))
        assert captured["route"] == f"channels/{cid}/clone"
        assert captured["body"].id == cid
        assert isinstance(out, KronicleChannel)

    def test_uuid_id_no_body(self, setup, monkeypatch):
        cid = uuid4()
        monkeypatch.setattr(setup, "post", lambda *, route, body, **kw: channel_dict(cid))
        out = setup.clone_channel(cid)
        assert isinstance(out, KronicleChannel)

    def test_channel_body_gets_new_id(self, setup, monkeypatch):
        cid = uuid4()
        other = uuid4()
        captured = {}

        def mock_post(*, route, body, **kw):
            captured["body"] = body
            return channel_dict(cid)

        monkeypatch.setattr(setup, "post", mock_post)
        body = KronicleChannel(id=other, name="Channel_1")
        setup.clone_channel(cid, body=body)
        assert captured["body"] is body
        assert body.id == cid

    def test_dict_body_gets_new_id(self, setup, monkeypatch):
        cid = uuid4()
        captured = {}

        def mock_post(*, route, body, **kw):
            captured["body"] = body
            return channel_dict(cid, name="Channel_2")

        monkeypatch.setattr(setup, "post", mock_post)
        setup.clone_channel(cid, body={"name": "Channel_2"})
        assert captured["body"].id == cid
        assert captured["body"].name == "Channel_2"
