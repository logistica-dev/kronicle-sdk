# tests/connectors/test_kronicle_auth.py
import json

import pytest
import requests

from kronicle_sdk.conf.read_conf import ConnectionInformation
from kronicle_sdk.connectors.abc_connector import KronicleAbstractConnector
from kronicle_sdk.connectors.auth.kronicle_auth import KronicleUsrLogin
from kronicle_sdk.models.iso_datetime import IsoDateTime
from kronicle_sdk.models.kronicle_errors import (
    KronicleConnectionError,
    KronicleResponseError,
)
from kronicle_sdk.utils.str_utils import encode_b64url


def make_response(payload, *, status_code=200, reason="OK", method="GET", url="http://test.local/x"):
    """Build a real requests.Response so pyright and requests' internals stay happy."""
    response = requests.Response()
    response.status_code = status_code
    response.reason = reason
    response.encoding = "utf-8"
    response._content = json.dumps(payload).encode("utf-8")
    request = requests.PreparedRequest()
    request.prepare(method=method, url=url)
    response.request = request
    return response


def make_jwt(exp):
    header = encode_b64url(json.dumps({"alg": "none", "typ": "JWT"}))
    payload = encode_b64url(json.dumps({"exp": exp}))
    return f"{header}.{payload}.signature"


def make_jwt_without_exp():
    header = encode_b64url(json.dumps({"alg": "none", "typ": "JWT"}))
    payload = encode_b64url(json.dumps({"sub": "admin"}))
    return f"{header}.{payload}.signature"


@pytest.fixture
def login():
    return KronicleUsrLogin(url="http://localhost:8765", usr="admin", pwd="secret")


class TestKronicleUsrLoginBasics:
    def test_prefix(self, login):
        assert login.prefix == "/auth/v1"

    def test_from_connection_info(self):
        co = ConnectionInformation(host="localhost", port=8000, usr="svc", pwd="pw")
        obj = KronicleUsrLogin.from_connection_info(co)
        assert isinstance(obj, KronicleUsrLogin)
        assert obj.url == "http://localhost:8000"
        assert obj.usr == "svc"
        assert obj.pwd == "pw"


class TestJwtProperty:
    def test_returns_cached_valid_jwt(self, login, monkeypatch):
        token = make_jwt(int(IsoDateTime.now_timestamp()) + 3600)
        login._jwt = token

        def fake_post(**kwargs):
            raise AssertionError("post should not be called for a cached valid jwt")

        monkeypatch.setattr("kronicle_sdk.connectors.auth.kronicle_auth.post", fake_post)
        assert login.jwt == token

    def test_login_success(self, login, monkeypatch):
        token = make_jwt(int(IsoDateTime.now_timestamp()) + 3600)

        def fake_post(**kwargs):
            assert kwargs["json"] == {"login": "admin", "password": "secret"}
            return make_response({"access_token": token})

        monkeypatch.setattr("kronicle_sdk.connectors.auth.kronicle_auth.post", fake_post)
        assert login.jwt == token
        assert login._jwt == token
        assert login._exp is None

    def test_login_failure_raises_connection_error(self, login, monkeypatch):
        def fake_post(**kwargs):
            return make_response(
                {"detail": {"message": "bad credentials", "error": "Unauthorized"}},
                status_code=401,
                reason="Unauthorized",
            )

        monkeypatch.setattr("kronicle_sdk.connectors.auth.kronicle_auth.post", fake_post)
        with pytest.raises(KronicleConnectionError, match="Failed to get a JWT"):
            _ = login.jwt


class TestRenewJwtFromRes:
    def test_valid_token_sets_jwt_and_resets_exp(self, login):
        login._exp = 999
        result = login._renew_jwt_from_res({"access_token": "abc.def.ghi"})
        assert result == "abc.def.ghi"
        assert login._jwt == "abc.def.ghi"
        assert login._exp is None

    def test_missing_access_token_raises(self, login):
        with pytest.raises(KronicleResponseError, match="No field 'access_token'"):
            login._renew_jwt_from_res({})

    def test_non_string_access_token_raises(self, login):
        with pytest.raises(KronicleResponseError):
            login._renew_jwt_from_res({"access_token": 123})


class TestAuthHeaders:
    def test_auth_headers(self, login):
        token = make_jwt(int(IsoDateTime.now_timestamp()) + 3600)
        login._jwt = token
        assert login.auth_headers == {"Authorization": f"Bearer {token}"}


class TestJwtExp:
    def test_no_jwt_returns_zero(self, login):
        login._jwt = None
        assert login.jwt_exp == 0

    def test_cached_exp_is_returned(self, login):
        login._jwt = "not-a-real-jwt"
        login._exp = 123456
        assert login.jwt_exp == 123456

    def test_exp_decoded_from_jwt_and_cached(self, login):
        exp = int(IsoDateTime.now_timestamp()) + 3600
        login._jwt = make_jwt(exp)
        login._exp = None
        assert login.jwt_exp == exp
        assert login._exp == exp

    def test_exp_absent_falls_back_to_zero(self, login):
        login._jwt = make_jwt_without_exp()
        login._exp = None
        assert login.jwt_exp == 0
        assert login._exp == 0


class TestIsJwtValid:
    def test_no_jwt_is_invalid(self, login):
        login._jwt = None
        assert login.is_jwt_valid() is False

    def test_future_exp_is_valid(self, login):
        login._jwt = make_jwt(int(IsoDateTime.now_timestamp()) + 3600)
        login._exp = None
        assert login.is_jwt_valid() is True

    def test_past_exp_is_invalid(self, login):
        login._jwt = make_jwt(int(IsoDateTime.now_timestamp()) - 3600)
        login._exp = None
        assert login.is_jwt_valid() is False


class TestRequestOverride:
    def test_request_adds_authorization_header(self, login, monkeypatch):
        token = make_jwt(int(IsoDateTime.now_timestamp()) + 3600)
        login._jwt = token
        captured = {}
        sentinel = object()

        def fake_super_request(self, method, route=None, body=None, **kwargs):
            captured["method"] = method
            captured["route"] = route
            captured["headers"] = kwargs["headers"]
            return sentinel

        monkeypatch.setattr(KronicleAbstractConnector, "_request", fake_super_request)
        result = login._request(requests.get, route="whatever")
        assert result is sentinel
        assert captured["method"] is requests.get
        assert captured["route"] == "whatever"
        assert captured["headers"]["Authorization"] == f"Bearer {token}"

    def test_request_preserves_existing_headers(self, login, monkeypatch):
        token = make_jwt(int(IsoDateTime.now_timestamp()) + 3600)
        login._jwt = token
        captured = {}

        def fake_super_request(self, method, route=None, body=None, **kwargs):
            captured["headers"] = kwargs["headers"]
            return None

        monkeypatch.setattr(KronicleAbstractConnector, "_request", fake_super_request)
        login._request(requests.get, route="x", headers={"X-Test": "1"})
        assert captured["headers"] == {"X-Test": "1", "Authorization": f"Bearer {token}"}


class TestChangePassword:
    def test_change_password_returns_new_jwt(self, login, monkeypatch):
        token = make_jwt(int(IsoDateTime.now_timestamp()) + 3600)
        captured = {}

        def fake_post(route, body):
            captured["route"] = route
            captured["body"] = body
            return {"access_token": token}

        monkeypatch.setattr(login, "post", fake_post)
        result = login.change_password("NewPass123!")
        assert result == token
        assert login._jwt == token
        assert captured["route"] == "/change_password"
        assert captured["body"] == {
            "login": "admin",
            "password": "secret",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        }
