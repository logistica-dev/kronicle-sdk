# tests/connectors/test_abc_connector.py
import json
from uuid import uuid1, uuid4

import pytest
from requests import PreparedRequest, Response
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout as RequestsTimeout

from kronicle_sdk.connectors import abc_connector as abc
from kronicle_sdk.connectors.abc_connector import KronicleAbstractConnector
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.kronicle_errors import (
    KronicleConnectionError,
    KronicleHTTPError,
    KronicleHTTPErrorModel,
    KronicleOperationError,
    KronicleResponseError,
)


def _fill(
    r: Response,
    status=200,
    payload=None,
    *,
    text=None,
    reason="OK",
    method="GET",
    url="http://host/x",
) -> Response:
    r.status_code = status
    r.reason = reason
    r.encoding = "utf-8"
    r._content = (
        (text.encode() if isinstance(text, str) else text) if text is not None else json.dumps(payload).encode()
    )
    req = PreparedRequest()
    req.method = method
    req.url = url
    r.request = req
    return r


def make_response(status=200, payload=None, **kwargs) -> Response:
    return _fill(Response(), status, payload, **kwargs)


class FlakyResponse(Response):
    """A real Response whose ``json()`` succeeds once then fails.

    Needed to reach the JSON-decode guard inside ``_parse``: the first
    ``json()`` call (line 108) must succeed, the second one (line 116) must fail.
    """

    def __init__(self):
        super().__init__()
        self._calls = 0

    def json(self, **kwargs):
        self._calls += 1
        if self._calls >= 2:
            raise ValueError("not json")
        return super().json(**kwargs)


def make_flaky_response(status=200, payload=None, **kwargs) -> Response:
    return _fill(FlakyResponse(), status, payload, **kwargs)


class KronicleDummy(KronicleAbstractConnector):
    """Minimal concrete connector. Named ``Kronicle*`` to cover the log-name branch."""

    @property
    def prefix(self) -> str:
        return "/api/v1"


@pytest.fixture
def conn():
    return KronicleDummy(url="http://host")


class TestPrefixJoinAndHelpers:
    def test_abstract_prefix_body_raises(self):
        fget = KronicleAbstractConnector.prefix.fget
        assert fget is not None
        with pytest.raises(NotImplementedError):
            fget(object())

    def test_init_defaults(self):
        c = KronicleDummy()
        assert c.url == "http://127.0.0.1:8000"
        assert c.timeout == 3
        assert c._retries == 2
        assert c._delay == 2

    def test_join_default_prefix(self, conn):
        assert conn._join_url("/channels") == "http://host/api/v1/channels"

    def test_join_prefix_override(self, conn):
        assert conn._join_url("/channels", prefix="/data/v1") == "http://host/data/v1/channels"

    def test_join_none_route(self, conn):
        assert conn._join_url(None) == "http://host/api/v1"

    def test_method_str(self):
        assert KronicleAbstractConnector.method_str(abc.get) == "GET"


class TestAttempt:
    def test_success_returns_value(self, conn):
        assert conn._attempt(lambda: 42) == 42

    def test_retries_then_succeeds(self, conn):
        conn._delay = 0
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 2:
                raise RequestsConnectionError("boom")
            return "ok"

        assert conn._attempt(flaky) == "ok"
        assert calls["n"] == 2

    def test_timeout_is_retried(self, conn):
        conn._delay = 0
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            raise RequestsTimeout("slow")

        with pytest.raises(KronicleConnectionError) as exc_info:
            conn._attempt(flaky)
        assert calls["n"] == conn._retries
        assert isinstance(exc_info.value.__cause__, RequestsTimeout)

    def test_exhausted_wraps_last_error(self, conn):
        conn._delay = 0
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            raise RequestsConnectionError("boom")

        with pytest.raises(KronicleConnectionError):
            conn._attempt(flaky)
        assert calls["n"] == conn._retries

    def test_non_retriable_not_retried(self, conn):
        calls = {"n": 0}

        def bad():
            calls["n"] += 1
            raise ValueError("nope")

        with pytest.raises(ValueError):
            conn._attempt(bad)
        assert calls["n"] == 1

    def test_explicit_retries_and_delay(self, conn):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            raise RequestsConnectionError("boom")

        with pytest.raises(KronicleConnectionError):
            conn._attempt(flaky, retries=1, delay=0)
        assert calls["n"] == 1


class TestParse:
    def test_none_response_raises(self, conn):
        with pytest.raises(KronicleResponseError):
            conn._parse(None)  # type: ignore[arg-type]

    def test_non_ok_without_log(self, conn):
        r = make_response(404, {"message": "nope", "error": "NotFound"})
        with pytest.raises(KronicleHTTPError) as exc_info:
            conn._parse(r)
        assert exc_info.value.status == 404

    def test_non_ok_with_log(self, conn):
        r = make_response(422, {"error": "x", "message": "bad"})
        with pytest.raises(KronicleHTTPError):
            conn._parse(r, url="http://host/x", method="POST", should_log=True, params={"a": 1})

    def test_ok_with_log(self, conn):
        r = make_response(200, {"ok": True})
        assert conn._parse(r, should_log=True) == {"ok": True}

    def test_ok_invalid_json_raises_response_error(self, conn):
        # json() succeeds on the first call and fails on the second, reaching the guard.
        r = make_flaky_response(200, {"ok": True})
        with pytest.raises(KronicleResponseError):
            conn._parse(r)

    def test_ok_non_json_text_raises_response_error(self, conn):
        r = make_response(200, text="not json")
        with pytest.raises(KronicleResponseError):
            conn._parse(r)

    def test_non_ok_non_json_body_raises_http_error(self, conn):
        r = make_response(500, text="<html>boom</html>", reason="Server Error")
        with pytest.raises(KronicleHTTPError) as exc_info:
            conn._parse(r)
        assert exc_info.value.status == 500


class TestRequest:
    def test_get_does_not_invalidate_cache(self, conn, monkeypatch):
        calls = {"n": 0}
        monkeypatch.setattr(conn, "_invalidate_cache", lambda: calls.__setitem__("n", calls["n"] + 1))
        captured = {}

        def get(*, url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return make_response(200, {"ok": True})

        result = conn._request(get, "/channels")
        assert result == {"ok": True}
        assert calls["n"] == 0
        assert captured["url"] == "http://host/api/v1/channels"
        assert "json" not in captured["kwargs"]
        assert captured["kwargs"]["timeout"] == 5

    def test_non_get_invalidates_cache(self, conn):
        def post(*, url, **kwargs):
            return make_response(200, {"ok": True})

        conn._request(post, "/channels")
        assert conn._metadata_cache is None

    def test_body_none(self, conn):
        captured = {}

        def get(*, url, **kwargs):
            captured.update(kwargs)
            return make_response(200, {"ok": True})

        conn._request(get, "/x", body=None)
        assert "json" not in captured

    def test_body_dict(self, conn):
        captured = {}

        def post(*, url, **kwargs):
            captured.update(kwargs)
            return make_response(200, {"ok": True})

        conn._request(post, "/x", body={"a": 1})
        assert captured["json"] == {"a": 1}

    def test_body_channel(self, conn):
        captured = {}

        def post(*, url, **kwargs):
            captured.update(kwargs)
            return make_response(200, {"ok": True})

        conn._request(post, "/x", body=KronicleChannel(name="chan_a"))
        assert captured["json"]["name"] == "chan_a"

    def test_body_invalid_type(self, conn):
        called = {"n": 0}

        def post(*, url, **kwargs):
            called["n"] += 1
            return make_response(200, {"ok": True})

        with pytest.raises(TypeError):
            conn._request(post, "/x", body=123)  # type: ignore[arg-type]
        assert called["n"] == 0

    def test_params_passed_through(self, conn):
        captured = {}

        def get(*, url, **kwargs):
            captured.update(kwargs)
            return make_response(200, {"ok": True})

        conn._request(get, "/x", params={"a": "1"})
        assert captured["params"] == {"a": "1"}

    def test_prefix_override(self, conn):
        captured = {}

        def get(*, url, **kwargs):
            captured["url"] = url
            return make_response(200, {"ok": True})

        conn._request(get, "/x", prefix="/data/v1")
        assert captured["url"] == "http://host/data/v1/x"

    def test_should_log(self, conn):
        def get(*, url, **kwargs):
            return make_response(200, {"ok": True})

        assert conn._request(get, "/x", should_log=True) == {"ok": True}

    def test_http_error_reraised(self, conn):
        def get(*, url, **kwargs):
            raise KronicleHTTPError(KronicleHTTPErrorModel(status=404, error="NotFound", message="nope"))

        with pytest.raises(KronicleHTTPError):
            conn._request(get, "/x")

    def test_generic_error_reraised(self, conn):
        def get(*, url, **kwargs):
            raise ValueError("boom")

        with pytest.raises(ValueError):
            conn._request(get, "/x")

    def test_get_retries_on_connection_error(self, conn):
        conn._delay = 0
        calls = {"n": 0}

        def get(*, url, **kwargs):
            calls["n"] += 1
            if calls["n"] < 2:
                raise RequestsConnectionError("boom")
            return make_response(200, {"ok": True})

        assert conn._request(get, "/x") == {"ok": True}
        assert calls["n"] == 2

    def test_get_exhausted_raises_connection_error(self, conn):
        conn._delay = 0
        calls = {"n": 0}

        def get(*, url, **kwargs):
            calls["n"] += 1
            raise RequestsConnectionError("boom")

        with pytest.raises(KronicleConnectionError):
            conn._request(get, "/x")
        assert calls["n"] == conn._retries

    def test_post_not_retried(self, conn):
        calls = {"n": 0}

        def post(*, url, **kwargs):
            calls["n"] += 1
            raise RequestsConnectionError("boom")

        with pytest.raises(RequestsConnectionError):
            conn._request(post, "/x")
        assert calls["n"] == 1


class TestSerializeAndValidate:
    def test_serialize_none(self, conn):
        assert conn._serialize_payload(None) is None

    def test_serialize_dict(self, conn):
        assert conn._serialize_payload({"a": 1}) == {"a": 1}

    def test_serialize_channel(self, conn):
        payload = conn._serialize_payload(KronicleChannel(name="chan_a"))
        assert payload is not None
        assert payload["name"] == "chan_a"

    def test_serialize_invalid(self, conn):
        with pytest.raises(TypeError):
            conn._serialize_payload(123)

    def test_ensure_is_payload_channel(self, conn):
        c = KronicleChannel(name="chan_a")
        assert conn._ensure_is_payload(c) is c

    def test_ensure_is_payload_dict(self, conn):
        c = conn._ensure_is_payload({"name": "chan_a"})
        assert isinstance(c, KronicleChannel)
        assert c.name == "chan_a"

    def test_ensure_is_payload_invalid(self, conn):
        with pytest.raises(TypeError):
            conn._ensure_is_payload("bad")

    def test_ensure_is_payload_or_none_falsy(self, conn):
        assert conn._ensure_is_payload_or_none(None) is None
        assert conn._ensure_is_payload_or_none({}) is None

    def test_ensure_is_payload_or_none_truthy(self, conn):
        c = conn._ensure_is_payload_or_none({"name": "chan_a"})
        assert c is not None
        assert c.name == "chan_a"

    def test_ensure_is_payload_list_not_a_list(self, conn):
        with pytest.raises(TypeError):
            conn._ensure_is_payload_list({"a": 1})

    def test_ensure_is_payload_list_bad_element(self, conn):
        with pytest.raises(TypeError):
            conn._ensure_is_payload_list([KronicleChannel(name="chan_a"), {"name": "chan_b"}])

    def test_ensure_is_payload_list_valid(self, conn):
        channels = [KronicleChannel(name="chan_a"), KronicleChannel(name="chan_b")]
        assert conn._ensure_is_payload_list(channels) == channels

    def test_to_kronicle_channel_dict(self, conn):
        assert isinstance(conn._to_kronicle_channel({"name": "chan_a"}), KronicleChannel)

    def test_to_kronicle_channel_channel(self, conn):
        c = KronicleChannel(name="chan_a")
        assert conn._to_kronicle_channel(c) is c

    def test_to_kronicle_channel_invalid(self, conn):
        with pytest.raises(KronicleOperationError):
            conn._to_kronicle_channel(123)

    def test_ensure_kronicle_channel_channel(self, conn):
        c = KronicleChannel(name="chan_a")
        assert conn._ensure_kronicle_channel(c) is c

    def test_ensure_kronicle_channel_dict(self, conn):
        assert isinstance(conn._ensure_kronicle_channel({"name": "chan_a"}), KronicleChannel)

    def test_ensure_payload_id_valid_channel(self, conn):
        cid = uuid4()
        assert conn._ensure_payload_id(KronicleChannel(id=cid)) == str(cid)

    def test_ensure_payload_id_from_dict(self, conn):
        cid = uuid4()
        assert conn._ensure_payload_id({"id": str(cid)}) == str(cid)

    def test_ensure_payload_id_missing(self, conn):
        c = KronicleChannel(name="chan_a")
        c.id = None
        with pytest.raises(ValueError, match="Channel ID missing"):
            conn._ensure_payload_id(c)

    def test_ensure_payload_id_not_v4(self, conn):
        c = KronicleChannel(name="chan_a")
        c.id = uuid1()
        with pytest.raises(ValueError):
            conn._ensure_payload_id(c)


class TestVerbWrappers:
    def test_get_wrapper(self, conn, monkeypatch):
        captured = {}

        def fake_get(*, url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return make_response(200, {"ok": True})

        monkeypatch.setattr(abc, "get", fake_get)
        result = conn.get("/channels", params={"a": "1"})
        assert result == {"ok": True}
        assert captured["url"] == "http://host/api/v1/channels"
        assert captured["kwargs"]["params"] == {"a": "1"}
        assert captured["kwargs"]["timeout"] == conn.timeout

    def test_post_wrapper(self, conn, monkeypatch):
        captured = {}

        def fake_post(*, url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return make_response(200, {"ok": True})

        monkeypatch.setattr(abc, "post", fake_post)
        conn.post("/channels", body={"name": "chan_a"})
        assert captured["url"] == "http://host/api/v1/channels"
        assert captured["kwargs"]["json"] == {"name": "chan_a"}

    def test_put_wrapper(self, conn, monkeypatch):
        captured = {}

        def fake_put(*, url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return make_response(200, {"ok": True})

        monkeypatch.setattr(abc, "put", fake_put)
        conn.put("/channels/1", {"name": "chan_a"})
        assert captured["url"] == "http://host/api/v1/channels/1"
        assert captured["kwargs"]["json"] == {"name": "chan_a"}

    def test_put_empty_body_raises(self, conn):
        with pytest.raises(ValueError):
            conn.put("/channels/1", {})

    def test_patch_wrapper(self, conn, monkeypatch):
        captured = {}

        def fake_patch(*, url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return make_response(200, {"ok": True})

        monkeypatch.setattr(abc, "patch", fake_patch)
        conn.patch("/channels/1", {"name": "chan_a"})
        assert captured["url"] == "http://host/api/v1/channels/1"
        assert captured["kwargs"]["json"] == {"name": "chan_a"}

    def test_patch_empty_body_raises(self, conn):
        with pytest.raises(ValueError):
            conn.patch("/channels/1", {})

    def test_delete_wrapper(self, conn, monkeypatch):
        captured = {}

        def fake_delete(*, url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return make_response(200, {"ok": True})

        monkeypatch.setattr(abc, "delete", fake_delete)
        conn.delete("/channels/1", params={"x": "y"})
        assert captured["url"] == "http://host/api/v1/channels/1"
        assert captured["kwargs"]["params"] == {"x": "y"}


class TestHealth:
    def test_is_alive_true(self, conn, monkeypatch):
        monkeypatch.setattr(abc, "get", lambda *, url, timeout: make_response(200, {"status": "alive"}))
        assert conn.is_alive() is True

    def test_is_alive_wrong_status(self, conn, monkeypatch):
        monkeypatch.setattr(abc, "get", lambda *, url, timeout: make_response(200, {"status": "ready"}))
        assert conn.is_alive() is False

    def test_is_alive_none(self, conn, monkeypatch):
        monkeypatch.setattr(abc, "get", lambda *, url, timeout: make_response(200, None))
        assert conn.is_alive() is False

    def test_is_ready_true(self, conn, monkeypatch):
        monkeypatch.setattr(abc, "get", lambda *, url, timeout: make_response(200, {"status": "ready"}))
        assert conn.is_ready() is True

    def test_is_ready_wrong_status(self, conn, monkeypatch):
        monkeypatch.setattr(abc, "get", lambda *, url, timeout: make_response(200, {"status": "alive"}))
        assert conn.is_ready() is False

    def test_is_ready_none(self, conn, monkeypatch):
        monkeypatch.setattr(abc, "get", lambda *, url, timeout: make_response(200, None))
        assert conn.is_ready() is False
