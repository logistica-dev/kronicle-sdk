# tests/connectors/test_abc_channel_connector.py
import json
from uuid import UUID, uuid4

import pytest
import requests

from kronicle_sdk.connectors.channel import abc_channel_connector
from kronicle_sdk.connectors.channel.abc_channel_connector import (
    KronicleAbstractChannelConnector,
)
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.data.row_filter import RowFilter
from kronicle_sdk.models.kronicle_errors import (
    KronicleHTTPError,
    KronicleHTTPErrorModel,
    KronicleResponseError,
)


def make_response(payload, *, status_code=200, reason="OK", method="GET", url="http://test.local/x"):
    """Build a real requests.Response so requests' internals stay happy."""
    response = requests.Response()
    response.status_code = status_code
    response.reason = reason
    response.encoding = "utf-8"
    response._content = json.dumps(payload).encode("utf-8")
    request = requests.PreparedRequest()
    request.prepare(method=method, url=url)
    response.request = request
    return response


def channel_dict(cid=None, name="Channel_1", **extra):
    d = {"id": str(cid or uuid4()), "name": name}
    d.update(extra)
    return d


def http_error(status):
    return KronicleHTTPError(KronicleHTTPErrorModel(status=status, error="err", message="nope"))


def raise_http(status):
    def _raise(*args, **kwargs):
        raise http_error(status)

    return _raise


class DummyChannelConnector(KronicleAbstractChannelConnector):
    """Concrete subclass exposing the abstract ``prefix`` for direct testing."""

    @property
    def prefix(self) -> str:
        return "/data/v1"


@pytest.fixture
def conn():
    c = DummyChannelConnector(url="http://localhost:8765", usr="admin", pwd="secret")
    # Pre-seed a non-expiring JWT so the auth layer never performs a real login.
    c._jwt = "fake-jwt"
    c._exp = 4102444800  # year 2100
    return c


class TestAbstractPrefix:
    def test_abstract_prefix_body_raises(self, conn):
        fget = KronicleAbstractChannelConnector.prefix.fget
        assert fget is not None
        with pytest.raises(NotImplementedError):
            fget(conn)


class TestParse:
    def test_strict_false_returns_raw(self, conn):
        resp = make_response([{"whatever": 1}])
        assert conn._parse(resp, strict=False) == [{"whatever": 1}]

    def test_dict_returns_channel(self, conn):
        resp = make_response(channel_dict())
        out = conn._parse(resp)
        assert isinstance(out, KronicleChannel)

    def test_list_returns_channels(self, conn):
        resp = make_response([channel_dict(), channel_dict(name="Channel_2")])
        out = conn._parse(resp)
        assert isinstance(out, list)
        assert all(isinstance(c, KronicleChannel) for c in out)

    def test_invalid_dict_shape_raises(self, conn):
        resp = make_response({"id": "not-a-uuid"})
        with pytest.raises(KronicleResponseError):
            conn._parse(resp)

    def test_non_dict_list_raises(self, conn):
        resp = make_response(42)
        with pytest.raises(KronicleResponseError):
            conn._parse(resp)


class TestRequestDelegation:
    """Exercise the channel ``_request`` override through the module-level requests verbs."""

    def test_get_delegates_to_super(self, conn, monkeypatch):
        captured = {}

        def fake_get(*, url, **kwargs):
            captured["url"] = url
            return make_response(channel_dict())

        monkeypatch.setattr(abc_channel_connector, "get", fake_get)
        out = conn.get(route="channels")
        assert isinstance(out, KronicleChannel)
        assert captured["url"] == "http://localhost:8765/data/v1/channels"

    def test_post_delegates_to_super(self, conn, monkeypatch):
        sent = {}

        def fake_post(*, url, **kwargs):
            sent["json"] = kwargs.get("json")
            return make_response(channel_dict())

        monkeypatch.setattr(abc_channel_connector, "post", fake_post)
        out = conn.post(route="channels", body=KronicleChannel(name="Channel_1"))
        assert isinstance(out, KronicleChannel)
        assert sent["json"]["name"] == "Channel_1"

    def test_put_delegates_to_super(self, conn, monkeypatch):
        monkeypatch.setattr(abc_channel_connector, "put", lambda *, url, **kw: make_response(channel_dict()))
        out = conn.put(route="channels", body={"name": "Channel_1"})
        assert isinstance(out, KronicleChannel)

    def test_put_empty_body_raises(self, conn):
        with pytest.raises(ValueError):
            conn.put(route="channels", body={})

    def test_patch_delegates_to_super(self, conn, monkeypatch):
        monkeypatch.setattr(abc_channel_connector, "patch", lambda *, url, **kw: make_response(channel_dict()))
        out = conn.patch(route="channels", body={"name": "Channel_1"})
        assert isinstance(out, KronicleChannel)

    def test_patch_empty_body_raises(self, conn):
        with pytest.raises(ValueError):
            conn.patch(route="channels", body={})

    def test_delete_delegates_to_super(self, conn, monkeypatch):
        monkeypatch.setattr(abc_channel_connector, "delete", lambda *, url, **kw: make_response(channel_dict()))
        out = conn.delete(route="channels/abc")
        assert isinstance(out, KronicleChannel)


class TestInternalHelpers:
    def test_invalidate_cache(self, conn):
        conn._metadata_cache = [KronicleChannel(name="Channel_1")]
        conn._invalidate_cache()
        assert conn._metadata_cache is None

    def test_serialize_none(self, conn):
        assert conn._serialize_payload(None) is None

    def test_serialize_channel(self, conn):
        out = conn._serialize_payload(KronicleChannel(name="Channel_1"))
        assert out["name"] == "Channel_1"

    def test_serialize_dict(self, conn):
        out = conn._serialize_payload({"name": "Channel_1"})
        assert out["name"] == "Channel_1"

    def test_serialize_invalid_type(self, conn):
        with pytest.raises(TypeError):
            conn._serialize_payload(123)


class TestListAndCache:
    def test_list_channels(self, conn, monkeypatch):
        def mock_get(*, route, params=None, **kw):
            assert route == "channels"
            return [KronicleChannel(name="Channel_1"), KronicleChannel(name="Channel_2")]

        monkeypatch.setattr(conn, "get", mock_get)
        channels = conn.list_channels()
        assert len(channels) == 2
        assert all(isinstance(c, KronicleChannel) for c in channels)

    def test_all_channels_caches(self, conn, monkeypatch):
        calls = {"n": 0}

        def mock_list():
            calls["n"] += 1
            return [KronicleChannel(name="Channel_1")]

        monkeypatch.setattr(conn, "list_channels", mock_list)
        first = conn.all_channels
        second = conn.all_channels
        assert first is second
        assert calls["n"] == 1

    def test_all_channels_when_cache_is_none(self, conn, monkeypatch):
        conn._metadata_cache = None
        monkeypatch.setattr(conn, "list_channels", lambda: [KronicleChannel(name="Channel_1")])
        assert len(conn.all_channels) == 1

    def test_all_ids(self, conn, monkeypatch):
        cid = uuid4()
        monkeypatch.setattr(conn, "list_channels", lambda: [KronicleChannel(id=cid, name="Channel_1")])
        assert conn.all_ids == [cid]


class TestGetChannel:
    def test_get_channel_by_id_found(self, conn, monkeypatch):
        cid = uuid4()
        existing = KronicleChannel(id=cid, name="Channel_1")

        def mock_by_id(id):
            assert isinstance(id, UUID)
            return existing

        monkeypatch.setattr(conn, "get_channel_by_id", mock_by_id)
        assert conn.get_channel(KronicleChannel(id=cid, name="Channel_1")) is existing

    def test_get_channel_404_falls_back_to_name(self, conn, monkeypatch):
        cid = uuid4()
        existing = KronicleChannel(name="Channel_1")
        monkeypatch.setattr(conn, "get_channel_by_id", raise_http(404))
        monkeypatch.setattr(conn, "get_channel_by_name", lambda name: existing)
        assert conn.get_channel(KronicleChannel(id=cid, name="Channel_1")) is existing

    def test_get_channel_404_name_missing_returns_none(self, conn, monkeypatch):
        monkeypatch.setattr(conn, "get_channel_by_id", raise_http(404))
        monkeypatch.setattr(conn, "get_channel_by_name", lambda name: None)
        assert conn.get_channel(KronicleChannel(name="Channel_1")) is None

    def test_get_channel_non_404_reraises(self, conn, monkeypatch):
        monkeypatch.setattr(conn, "get_channel_by_id", raise_http(500))
        with pytest.raises(KronicleHTTPError):
            conn.get_channel(KronicleChannel(id=uuid4(), name="Channel_1"))

    def test_get_channel_no_id_uses_name(self, conn, monkeypatch):
        existing = KronicleChannel(name="Channel_1")
        monkeypatch.setattr(conn, "get_channel_by_name", lambda name: existing)
        channel = KronicleChannel(name="Channel_1")
        channel.id = None
        assert conn.get_channel(channel) is existing

    def test_get_channel_empty_returns_none(self, conn):
        channel = KronicleChannel()
        channel.id = None
        channel.name = None
        assert conn.get_channel(channel) is None

    def test_get_channel_by_id(self, conn, monkeypatch):
        cid = uuid4()

        def mock_get(*, route, params=None, **kw):
            assert str(cid) in route
            return channel_dict(cid=cid)

        monkeypatch.setattr(conn, "get", mock_get)
        out = conn.get_channel_by_id(cid)
        assert out is not None
        assert out.id == cid

    def test_get_channel_by_id_none(self, conn, monkeypatch):
        monkeypatch.setattr(conn, "get", lambda *, route, **kw: None)
        assert conn.get_channel_by_id(uuid4()) is None

    def test_get_channel_by_name_found(self, conn, monkeypatch):
        def mock_get(*, route, strict=False, **kw):
            assert route.startswith("channels/?name=")
            assert strict is False
            return channel_dict()

        monkeypatch.setattr(conn, "get", mock_get)
        out = conn.get_channel_by_name("Channel One")
        assert out is not None

    def test_get_channel_by_name_absent(self, conn, monkeypatch):
        monkeypatch.setattr(conn, "get", lambda *, route, strict=False, **kw: None)
        assert conn.get_channel_by_name("Channel One") is None

    def test_get_channel_with_tags(self, conn, monkeypatch):
        captured = {}

        def mock_get(*, route, **kw):
            captured["route"] = route
            return [KronicleChannel(name="Channel_1")]

        monkeypatch.setattr(conn, "get", mock_get)
        out = conn.get_channel_with_tags({"Room": "A"})
        assert len(out) == 1
        assert "channels/?tags=" in captured["route"]

    def test_get_channel_with_meta(self, conn, monkeypatch):
        captured = {}

        def mock_get(*, route, **kw):
            captured["route"] = route
            return [KronicleChannel(name="Channel_1")]

        monkeypatch.setattr(conn, "get", mock_get)
        out = conn.get_channel_with_meta({"Unit": "C"})
        assert len(out) == 1
        assert "channels/?metadata=" in captured["route"]

    def test_get_channel_with_max_rows(self, conn, monkeypatch):
        c1 = KronicleChannel(name="Channel_1", available_rows=2)
        c2 = KronicleChannel(name="Channel_2", available_rows=9)
        c3 = KronicleChannel(name="Channel_3")  # available_rows None -> treated as 0
        monkeypatch.setattr(conn, "list_channels", lambda: [c1, c3, c2])
        assert conn.get_channel_with_max_rows() is c2

    def test_get_channel_with_max_rows_empty(self, conn, monkeypatch):
        monkeypatch.setattr(conn, "list_channels", lambda: [])
        assert conn.get_channel_with_max_rows() is None


class TestRowsAndColumns:
    def _mock_payload(self, conn, monkeypatch, channel):
        monkeypatch.setattr(conn, "get", lambda *, route, params=None, **kw: channel)

    def test_get_rows_str(self, conn, monkeypatch):
        self._mock_payload(conn, monkeypatch, KronicleChannel(rows=[{"a": 1}]))
        assert conn.get_rows_for_channel(uuid4(), "str") == str([{"a": 1}])

    def test_get_rows_list_and_dict(self, conn, monkeypatch):
        self._mock_payload(conn, monkeypatch, KronicleChannel(rows=[{"a": 1}]))
        cid = uuid4()
        assert conn.get_rows_for_channel(cid, "list") == [{"a": 1}]
        assert conn.get_rows_for_channel(cid, "dict") == [{"a": 1}]

    def test_get_rows_with_filter_passes_params(self, conn, monkeypatch):
        captured = {}

        def mock_get(*, route, params=None, **kw):
            captured["params"] = params
            return KronicleChannel(rows=[{"a": 1}])

        monkeypatch.setattr(conn, "get", mock_get)
        conn.get_rows_for_channel(uuid4(), "list", RowFilter(limit=5))
        assert captured["params"] == {"limit": 5}

    def test_get_rows_invalid_return_type(self, conn, monkeypatch):
        self._mock_payload(conn, monkeypatch, KronicleChannel(rows=[]))
        with pytest.raises(ValueError):
            conn.get_rows_for_channel(uuid4(), "json")  # type: ignore

    def test_get_cols_str(self, conn, monkeypatch):
        self._mock_payload(conn, monkeypatch, KronicleChannel(columns={"a": [1]}))
        assert conn.get_cols_for_channel(uuid4(), "str") == str({"a": [1]})

    def test_get_cols_dict_and_list(self, conn, monkeypatch):
        self._mock_payload(conn, monkeypatch, KronicleChannel(columns={"a": [1]}))
        cid = uuid4()
        assert conn.get_cols_for_channel(cid, "dict") == {"a": [1]}
        assert conn.get_cols_for_channel(cid, "list") == {"a": [1]}

    def test_get_cols_with_filter_passes_params(self, conn, monkeypatch):
        captured = {}

        def mock_get(*, route, params=None, **kw):
            captured["params"] = params
            return KronicleChannel(columns={"a": [1]})

        monkeypatch.setattr(conn, "get", mock_get)
        conn.get_cols_for_channel(uuid4(), "dict", RowFilter(columns="a"))
        assert captured["params"] == {"columns": "a"}

    def test_get_cols_invalid_return_type(self, conn, monkeypatch):
        self._mock_payload(conn, monkeypatch, KronicleChannel(columns={"a": [1]}))
        with pytest.raises(ValueError):
            conn.get_cols_for_channel(uuid4(), "xml")  # type: ignore
