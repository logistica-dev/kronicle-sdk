# kronicle/connectors/abc_connector.py
from abc import ABC, abstractmethod
from collections.abc import Callable
from time import sleep
from typing import Any

from requests import Response, delete, get, patch, post, put
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout as RequestsTimeout

from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.kronicle_errors import (
    KronicleConnectionError,
    KronicleHTTPError,
    KronicleOperationError,
    KronicleResponseError,
)
from kronicle_sdk.utils.log import log_d, log_e, log_w
from kronicle_sdk.utils.str_utils import (
    check_is_uuid4,
    get_type,
    param_dict_to_str,
    slash_join,
)


class KronicleAbstractConnector(ABC):
    """
    Abstract class that implements generic connection
    methods towards Kronicle.

    Args:
    url: Base URL of the Kronicle server.
    """

    def __init__(self, url: str = "http://127.0.0.1:8000"):
        self.url = url
        self._retries: int = 2
        self._delay: int = 2
        self.timeout: int = 3  # seconds

    @property
    @abstractmethod
    def prefix(self) -> str:
        raise NotImplementedError("Define a route prefix such as 'api/v1', 'data/v1', 'setup/v1', 'auth/v1'...")

    def _join_url(self, route: str | None, *, prefix: str | None = None) -> str:
        """
        Join the base URL, a prefix, and a route into a full URL.

        Args:
            route: route path appended after the prefix (may be None).
            prefix: override this call's prefix. Defaults to the connector's ``prefix`` when None;
                an empty string is kept as-is, so it omits the prefix segment entirely.

        Returns:
            The joined URL, with None/empty fragments skipped.
        """
        return slash_join(self.url, prefix if prefix is not None else self.prefix, route)

    # ----------------------------------------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------------------------------------
    #: Connection-level failures (``requests.ConnectionError`` / ``Timeout``) are retried only for
    #: these idempotent methods, so a retry can never duplicate a write (``POST`` / ``PATCH`` are
    #: attempted once).
    _retriable_methods: frozenset[str] = frozenset({"GET", "HEAD", "PUT", "DELETE"})

    def _attempt(self, func: Callable[[], Any], retries: int | None = None, delay: float | None = None) -> Any:
        """
        Call ``func``, retrying only on connection-level errors.

        ``requests`` connection errors and timeouts are retried up to ``retries`` times, sleeping
        ``delay`` seconds between attempts. HTTP errors and malformed responses are never retried.
        When all attempts fail, the last error is chained into a ``KronicleConnectionError``.
        """
        here = "_attempt"
        retries = retries if retries is not None else self._retries
        delay = delay if delay is not None else self._delay
        last_exc: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                return func()
            except (RequestsConnectionError, RequestsTimeout) as exc:
                last_exc = exc
                log_w(here, f"[attempt {attempt}/{retries}] retriable connection error", exc)
                if attempt < retries:
                    sleep(delay)

        raise KronicleConnectionError(f"Failed after {retries} attempts") from last_exc

    @staticmethod
    def method_str(method: Callable) -> str:
        return method.__name__.upper()
        # return f"{method}".split(" ")[1].upper()

    def _parse(
        self,
        response: Response,
        *,
        url: str | None = None,
        method: str | None = None,
        should_log: bool = False,
        params: dict | None = None,
        **kwargs,
    ) -> Any:
        """
        Parse a requests.Response object into validated KronicleChannel(s).

        Raises:
            KronicleResponseError: If the response is invalid or not JSON.
        """
        here = "_parse"
        if response is None:
            raise KronicleResponseError("No response received from Kronicle")

        try:
            res_content = response.json() if hasattr(response, "json") else response.content
        except Exception as exc:
            if not response.ok:
                # Non-JSON error body: let from_response build a KronicleHTTPError.
                raise KronicleHTTPError.from_response(response, url=url, method=method, params=params) from exc
            raise KronicleResponseError(f"Failed to decode JSON: {response.content}") from exc

        if not response.ok:
            if should_log:
                log_e(here, "Request failed", method, url, params or {}, "<=", res_content)
            raise KronicleHTTPError.from_response(response, url=url, method=method, params=params)
        if should_log:
            log_d(here, "Response received", res_content)
        try:
            data = response.json()
        except Exception as exc:
            raise KronicleResponseError(f"Failed to decode JSON: {response.content}") from exc
        return data

    def _request(
        self,
        method: Callable,
        route: str | None,
        body: KronicleChannel | dict | None = None,
        *,
        strict: bool = True,
        should_log: bool = False,
        prefix: str | None = None,
        params: dict | None = None,
        **kwargs,
    ) -> Any:
        """
        Execute an HTTP request with retries and validated payload.

        Retry only on connection-level errors; do not retry on HTTP 4xx/5xx
        or malformed responses.

        Args:
            method: requests HTTP method (get, post, put, delete, patch)
            route: route path to append to base URL
            body: optional payload (dict or KronicleChannel)
            strict: validate the response as KronicleChannel(s)
            prefix: override the class prefix (e.g. "/data/v1")
            params: URL query parameters
            kwargs: additional requests keyword arguments (timeout, headers, etc.)

        Raises:
            KronicleConnectionError: all retries exhausted
            KronicleHTTPError: HTTP 4xx/5xx response
            KronicleResponseError: response not JSON or invalid format
            TypeError: body type is invalid
        """
        here = f"{get_type(self)}.req"
        if here.startswith("Kronicle"):
            here = "K" + here[8:]
        # log_d(here, "prefix", prefix)
        url = self._join_url(route, prefix=prefix)
        method_str = self.method_str(method)
        if method_str != "GET":
            self._invalidate_cache()

        json_body = self._serialize_payload(body)
        request_kwargs = kwargs.copy()
        if params:
            request_kwargs["params"] = params
        if json_body is not None:
            request_kwargs["json"] = json_body
        request_kwargs.setdefault("timeout", getattr(self, "_timeout", 5))  # default timeout 5s
        # log_d(here, "request_kwargs", **request_kwargs)
        if should_log:
            log_d(here, "Request", method_str, url + param_dict_to_str(params))
        try:
            if method_str in self._retriable_methods:
                response: Response = self._attempt(lambda: method(url=url, **request_kwargs))
            else:
                response = method(url=url, **request_kwargs)
        except KronicleHTTPError as e:
            log_e(here, "KronicleHTTPError", f"{e}")
            raise
        except Exception as e:
            log_e(here, "type(exc)", get_type(e), e)
            log_d(here, "Request failed", method_str, url, "<=", get_type(e), e)
            raise
        return self._parse(response=response, strict=strict)

    def _invalidate_cache(self):
        self._metadata_cache = None

    def _serialize_payload(self, body) -> dict | None:
        if body is None:
            return None
        if isinstance(body, KronicleChannel):
            payload = body.model_dump(mode="json", exclude_none=True)
        elif isinstance(body, dict):
            payload = body
        else:
            raise TypeError(f"Invalid body type: {get_type(body)}")
        return payload

    @classmethod
    def _ensure_is_payload(cls, res) -> KronicleChannel:
        """Ensure the result is a KronicleChannel."""
        if isinstance(res, KronicleChannel):
            return res
        if isinstance(res, dict):
            return KronicleChannel.from_json(res)
        raise TypeError(f"KronicleChannel expected, got '{get_type(res)}' for {res}")

    @classmethod
    def _ensure_is_payload_or_none(cls, res) -> KronicleChannel | None:
        """Ensure the result is a KronicleChannel or None."""
        return None if not res else cls._ensure_is_payload(res)

    @classmethod
    def _ensure_is_payload_list(cls, res) -> list[KronicleChannel]:
        """Ensure the result is a list of KronicleChannel."""
        if not isinstance(res, list):
            raise TypeError(f"List expected, got '{get_type(res)}' for {res}")
        for res_i in res:
            if not isinstance(res_i, KronicleChannel):
                raise TypeError(
                    f"Each element of the list should be a KronicleChannel, got '{get_type(res_i)}' for {res_i}"
                )
        return res

    def _to_kronicle_channel(self, body: Any) -> KronicleChannel:
        if isinstance(body, dict):
            return KronicleChannel.from_json(body)
        if isinstance(body, KronicleChannel):
            return body
        raise KronicleOperationError(f"Expected a KronicleChannel, got a {get_type(body)}")

    def _ensure_kronicle_channel(self, body: KronicleChannel | dict) -> KronicleChannel:
        if isinstance(body, KronicleChannel):
            return body
        return KronicleChannel.from_json(body)

    def _ensure_payload_id(self, body: KronicleChannel | dict) -> str:
        here = "abc_connector._ensure_payload_id"
        log_d(here, "type(body)", get_type(body))
        log_d(here, "body", body)
        payload = self._ensure_kronicle_channel(body)
        log_d(here, "KronicleChannel", payload)

        if not (channel_id := payload.id):
            raise ValueError("Channel ID missing")
        return check_is_uuid4(channel_id)

    # ----------------------------------------------------------------------------------------------
    # HTTP verbs
    # ----------------------------------------------------------------------------------------------

    def get(
        self,
        route: str | None = None,
        *,
        prefix: str | None = None,
        params: dict | None = None,
        **kwargs,
    ) -> Any:
        """Perform a GET request and return validated payload(s)."""
        return self._request(
            get,
            route=route,
            prefix=prefix,
            timeout=self.timeout,
            params=params,
            **kwargs,
        )

    def post(
        self,
        route: str | None = None,
        body: KronicleChannel | dict | None = None,
        *,
        prefix: str | None = None,
        params: dict | None = None,
        **kwargs,
    ) -> Any:
        """Perform a POST request with validation."""
        return self._request(post, route=route, body=body, prefix=prefix, timeout=self.timeout, params=params, **kwargs)

    def put(
        self,
        route: str,
        body: KronicleChannel | dict,
        *,
        prefix: str | None = None,
        **kwargs,
    ) -> Any:
        """Perform a PUT request with validation."""
        if not body:
            raise ValueError("Please provide a body for this request")
        return self._request(put, route=route, body=body, prefix=prefix, timeout=self.timeout, **kwargs)

    def patch(
        self,
        route: str,
        body: KronicleChannel | dict,
        *,
        prefix: str | None = None,
        **kwargs,
    ) -> Any:
        """Perform a PATCH request with validation."""
        if not body:
            raise ValueError("Please provide a body for this request")
        return self._request(patch, route=route, prefix=prefix, timeout=self.timeout, body=body, **kwargs)

    def delete(
        self,
        route: str,
        *,
        prefix: str | None = None,
        params: dict | None = None,
        **kwargs,
    ) -> Any:
        """Perform a DELETE request and return validated payload(s)."""
        return self._request(
            delete,
            route=route,
            prefix=prefix,
            timeout=self.timeout,
            params=params,
            **kwargs,
        )

    # ----------------------------------------------------------------------------------------------
    # Health check
    # ----------------------------------------------------------------------------------------------
    def is_alive(self):
        res = self._parse(
            get(url=slash_join(self.url, "/health/live"), timeout=self.timeout),
            strict=False,
        )
        return isinstance(res, dict) and res.get("status") == "alive"

    def is_ready(self):
        res = self._parse(
            get(url=slash_join(self.url, "/health/ready"), timeout=self.timeout),
            strict=False,
        )
        return isinstance(res, dict) and res.get("status") == "ready"
