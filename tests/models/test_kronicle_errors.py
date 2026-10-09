# tests/models/test_kronicle_errors.py
import pytest
import requests

from kronicle_sdk.models.kronicle_errors import (
    KronicleConnectionError,
    KronicleError,
    KronicleHTTPError,
    KronicleHTTPErrorModel,
    KronicleOperationError,
    KronicleResponseError,
)


class FakeRequest:
    def __init__(self, method="GET", url="http://example.com/api"):
        self.method = method
        self.url = url


class FakeResponse(requests.Response):
    def __init__(
        self,
        status_code=200,
        json_data=None,
        json_exc=None,
        reason="OK",
        request=None,
        raise_exc=None,
    ):
        self.status_code = status_code
        self._json_data = json_data
        self._json_exc = json_exc
        self.reason = reason
        self.request = request  # type: ignore
        self._raise_exc = raise_exc
        self.raise_for_status_called = False

    def json(self):  # type: ignore
        if self._json_exc is not None:
            raise self._json_exc
        return self._json_data

    def raise_for_status(self):
        self.raise_for_status_called = True
        if self._raise_exc is not None:
            raise self._raise_exc


class FalsyJSONWithReason(dict):
    """Dict-like payload that also exposes a ``reason`` attribute."""

    reason = "Server exploded"


class ExplodingReasonResponse(requests.Response):
    """JSON parsing fails and reading ``reason`` fails too."""

    def __init__(self, status_code=500):
        self.status_code = status_code
        self.request = FakeRequest()  # type: ignore
        self.raise_for_status_called = False

    @property
    def reason(self):  # type: ignore
        raise RuntimeError("no reason available")

    def json(self):  # type: ignore
        raise ValueError("not json")

    def raise_for_status(self):
        self.raise_for_status_called = True


class TestExceptionHierarchy:
    def test_all_inherit_from_base(self):
        assert issubclass(KronicleConnectionError, KronicleError)
        assert issubclass(KronicleResponseError, KronicleError)
        assert issubclass(KronicleOperationError, KronicleError)
        assert issubclass(KronicleHTTPError, KronicleError)

    def test_simple_errors_carry_message(self):
        assert str(KronicleError("boom")) == "boom"
        assert str(KronicleConnectionError("down")) == "down"
        assert str(KronicleResponseError("bad")) == "bad"

    def test_operation_error_default_payload(self):
        err = KronicleOperationError("failed")
        assert str(err) == "failed"
        assert err.payload is None

    def test_operation_error_with_payload(self):
        err = KronicleOperationError("failed", payload={"op_status": "error"})
        assert str(err) == "failed"
        assert err.payload == {"op_status": "error"}


class TestHTTPErrorModel:
    def test_defaults(self):
        model = KronicleHTTPErrorModel(status=500, error="E", message="M")
        assert model.details is None
        assert model.method is None
        assert model.params is None
        assert model.url is None
        assert model.request_id is None

    def test_all_fields(self):
        model = KronicleHTTPErrorModel(
            status=404,
            error="NotFound",
            message="missing",
            details={"field": "id"},
            method="GET",
            params={"a": 1},
            url="http://example.com/x",
            request_id="req-1",
        )
        assert model.status == 404
        assert model.error == "NotFound"
        assert model.message == "missing"
        assert model.details == {"field": "id"}
        assert model.method == "GET"
        assert model.params == {"a": 1}
        assert model.url == "http://example.com/x"
        assert model.request_id == "req-1"


class TestHTTPErrorProperties:
    def _error(self, **overrides):
        fields = {
            "status": 418,
            "error": "Teapot",
            "message": "I am a teapot",
            "details": {"why": "short and stout"},
            "method": "POST",
            "params": {"x": "y"},
            "url": "http://example.com/teapot",
            "request_id": "abc-123",
        }
        fields.update(overrides)
        return KronicleHTTPError(KronicleHTTPErrorModel(**fields))

    def test_properties_delegate_to_model(self):
        err = self._error()
        assert err.status == 418
        assert err.error == "Teapot"
        assert err.message == "I am a teapot"
        assert err.details == {"why": "short and stout"}
        assert err.method == "POST"
        assert err.params == {"x": "y"}
        assert err.url == "http://example.com/teapot"
        assert err.request_id == "abc-123"

    def test_str_with_details(self):
        err = self._error()
        text = str(err)
        assert "418 Teapot: I am a teapot" in text
        assert "short and stout" in text
        assert "from request POST http://example.com/teapot" in text
        assert str(err) == err.args[0]

    def test_str_without_details(self):
        err = self._error(details=None)
        assert "(None)" in str(err)


class TestFromResponse:
    def test_none_response_raises(self):
        with pytest.raises(KronicleResponseError, match="No response content received"):
            KronicleHTTPError.from_response(None)  # type: ignore

    def test_422_delegates_to_pydantic(self):
        response = FakeResponse(
            status_code=422,
            json_data={"error": "ValidationError", "message": "bad payload"},
            request=FakeRequest("PUT", "http://example.com/rows"),
        )
        err = KronicleHTTPError.from_response(response)
        assert isinstance(err, KronicleHTTPError)
        assert err.status == 422
        assert err.error == "ValidationError"
        assert err.message == "bad payload"
        assert err.method == "PUT"
        assert err.url == "http://example.com/rows"

    def test_message_payload(self):
        response = FakeResponse(
            status_code=400,
            json_data={
                "status": 400,
                "error": "BadRequest",
                "message": "bad input",
                "details": {"field": "name"},
                "method": "POST",
                "url": "http://example.com/rows",
                "params": {"q": 1},
                "request_id": "req-9",
            },
            request=FakeRequest("POST", "http://example.com/rows"),
        )
        err = KronicleHTTPError.from_response(response)
        assert err.status == 400
        assert err.error == "BadRequest"
        assert err.message == "bad input"
        assert err.details == {"field": "name"}
        assert err.params == {"q": 1}
        assert err.request_id == "req-9"

    def test_message_payload_falls_back_to_path(self):
        response = FakeResponse(
            status_code=400,
            json_data={
                "status": 400,
                "error": "BadRequest",
                "message": "bad input",
                "path": "http://example.com/path-url",
            },
            request=FakeRequest("POST", "http://example.com/rows"),
        )
        err = KronicleHTTPError.from_response(response)
        assert err.url == "http://example.com/path-url"

    def test_message_payload_validation_error_falls_through(self):
        # `message` present but `status` missing -> model validation fails and the
        # inner except logs, then parsing continues to the `detail` branch.
        response = FakeResponse(
            status_code=422,
            json_data={"error": "E", "message": "M"},
            request=FakeRequest("POST", "http://example.com/x"),
        )
        # status_code 422 delegates earlier; use 400 here instead.
        response.status_code = 400
        err = KronicleHTTPError.from_response(response)
        # no detail, no reason path -> falls back to the default error branch
        assert err.status == 400

    def test_detail_payload(self):
        response = FakeResponse(
            status_code=400,
            json_data={"detail": {"message": "invalid", "error": "E", "details": {"k": "v"}}},
            request=FakeRequest("PATCH", "http://example.com/x"),
        )
        err = KronicleHTTPError.from_response(response)
        assert err.status == 400
        assert err.error == "E"
        assert err.message == "invalid"
        assert err.details == {"k": "v"}

    def test_empty_payload_uses_reason(self):
        response = FakeResponse(
            status_code=500,
            json_data=FalsyJSONWithReason(),
            request=FakeRequest("GET", "http://example.com/x"),
        )
        err = KronicleHTTPError.from_response(response)
        assert err.status == 500
        assert err.error == "Server exploded"
        assert err.message == "Server exploded"
        assert err.details == "Server exploded"

    def test_json_failure_falls_back_to_reason(self):
        response = FakeResponse(
            status_code=503,
            json_exc=ValueError("not json"),
            reason="Service Unavailable",
            request=FakeRequest("GET", "http://example.com/x"),
        )
        err = KronicleHTTPError.from_response(response)
        assert err.status == 503
        assert err.error == "Error 503"
        assert err.message == "Service Unavailable"
        assert err.details == "Service Unavailable"
        assert err.url == "http://example.com/x"
        assert err.method == "GET"

    def test_json_and_reason_failure_returns_no_response(self):
        response = ExplodingReasonResponse(status_code=500)
        err = KronicleHTTPError.from_response(response)
        assert response.raise_for_status_called is True
        assert err.status == 400
        assert err.error == "No response"
        assert err.message == "No response received from the server"
        assert err.method is None
        assert err.url is None

    def test_json_and_reason_failure_raise_for_status_propagates(self):
        response = ExplodingReasonResponse(status_code=500)
        response.raise_for_status = lambda: (_ for _ in ()).throw(RuntimeError("still broken"))
        with pytest.raises(RuntimeError, match="still broken"):
            KronicleHTTPError.from_response(response)


class TestFromPydanticResponse:
    def test_success_uses_defaults(self):
        response = FakeResponse(
            status_code=422,
            json_data={},
            request=FakeRequest("POST", "http://example.com/x"),
        )
        err = KronicleHTTPError.from_pydantic_response(response, params={"a": 1})
        assert err.status == 422
        assert err.error == "UnprocessableContent"
        assert err.message == "Incorrect payload"
        assert err.details is None
        assert err.method == "POST"
        assert err.url == "http://example.com/x"
        assert err.params == {"a": 1}

    def test_success_reads_fields(self):
        response = FakeResponse(
            status_code=422,
            json_data={"error": "E", "message": "M", "detail": {"k": "v"}},
            request=FakeRequest("POST", "http://example.com/x"),
        )
        err = KronicleHTTPError.from_pydantic_response(response)
        assert err.error == "E"
        assert err.message == "M"
        assert err.details == {"k": "v"}

    def test_success_uses_details_key_fallback(self):
        response = FakeResponse(
            status_code=422,
            json_data={"details": {"k": "v"}},
            request=FakeRequest("POST", "http://example.com/x"),
        )
        err = KronicleHTTPError.from_pydantic_response(response)
        assert err.details == {"k": "v"}

    def test_success_without_request_uses_args(self):
        response = FakeResponse(status_code=422, json_data={}, request=None)
        err = KronicleHTTPError.from_pydantic_response(response, url="fallback-url", method="fallback-method")
        assert err.url == "fallback-url"
        assert err.method == "fallback-method"

    def test_failure_returns_fallback_model(self):
        response = FakeResponse(
            status_code=400,
            json_exc=ValueError("bad json"),
            reason="Bad Request",
            request=None,
        )
        err = KronicleHTTPError.from_pydantic_response(response, url="U", method="M")
        assert response.raise_for_status_called is True
        assert err.status == 400
        assert err.error == "UnprocessableContent"
        assert err.message == "Incorrect payload"
        assert err.details == "Bad Request"
        assert err.url == "U"
        assert err.method == "M"
