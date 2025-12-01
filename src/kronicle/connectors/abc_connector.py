# connectors/abc_connector.py
from abc import ABC, abstractmethod
from time import sleep
from typing import Any, Literal, Tuple
from uuid import UUID

from pandas import DataFrame
from requests import Response, delete, get, patch, post, put

from kronicle.models.kronicle_errors import KronicleConnectionError, KronicleHTTPError, KronicleResponseError
from kronicle.models.kronicle_payload import KroniclePayload
from kronicle.utils.log import log_d, log_w
from kronicle.utils.str_utils import check_is_uuid4, get_type, slash_join


class KronicleAbstractConnector(ABC):
    """
    Abstract class that implements generic connection
    methods towards Kronicle.

    Args:
    url: Base URL of the Kronicle server.
    """

    def __init__(self, url: str = "http://127.0.0.1:8000"):
        self.url = url
        self._retries: int = 5
        self._delay: int = 2

    @property
    @abstractmethod
    def prefix(self) -> str:
        raise NotImplementedError("Define a route prefix such as 'api/v1', 'data/v1', or 'setup/v1'.")

    # ------------------------------------------------------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------------------------------------------------------

    def _join(self, route: str | None) -> str:
        """Join base URL, prefix, and route into a full URL."""
        return slash_join(self.url, self.prefix, route)

    def _parse(self, response: Response, *, strict=True, **params) -> KroniclePayload | list[KroniclePayload]:
        """
        Parse a requests.Response object into validated KroniclePayload(s).

        Raises:
            KronicleResponseError: If the response is invalid or not JSON.
        """
        if not response or not response.content:
            raise KronicleResponseError("No response content received from Kronicle")
        try:
            data = response.json()
        except Exception as exc:
            raise KronicleResponseError(f"Failed to decode JSON: {response.content}") from exc

        if not strict:
            return data

        try:
            if isinstance(data, dict):
                return KroniclePayload.from_json(data)

            if isinstance(data, list):
                return [KroniclePayload.from_json(d) for d in data]
        except Exception as exc:
            raise KronicleResponseError(
                f"Unexpected response format. Expected KroniclePayload or list[KroniclePayload], got: {response.content}"
            ) from exc

        raise KronicleResponseError(f"Unexpected response type: {get_type(data)}; expected dict or list")

    def _request(
        self,
        method,
        route,
        body: KroniclePayload | dict | None = None,
        strict: bool = True,
        **params,
    ) -> KroniclePayload | list[KroniclePayload]:
        """
        Execute an HTTP request with retries and validate payload types.

        Args:
            method: requests HTTP method function (get, post, put, delete)
            route: Kronicle route to call
            body: Optional body to send (dict or KroniclePayload)
            strict: True (default) if response should be validated as a
                KroniclePayload or a list[KroniclePayload]
            params: URL query parameters

        Raises:
            KronicleConnectionError: If all retries fail
            TypeError: If body is not dict or KroniclePayload
        """
        here = f"{get_type(self)}._request"
        url = self._join(route)
        json_body = None

        if body is not None:
            if isinstance(body, dict):
                payload = KroniclePayload.from_json(body)
            elif isinstance(body, KroniclePayload):
                payload = body
            else:
                raise TypeError(f"Invalid body type: {get_type(body)}")
            json_body = payload.model_dump_json()

        last_exc = None
        for _ in range(self._retries):
            try:
                response: Response = method(url=url, json=json_body, **params)
                if response.status_code >= 400:
                    raise KronicleHTTPError.from_response(response)
                return self._parse(response=response, strict=strict)
            except (KronicleResponseError, KronicleHTTPError) as exc:
                # Don't retry on response errors
                log_w(here, get_type(exc), exc)
                raise exc
            except Exception as exc:
                last_exc = exc
                sleep(self._delay)

        raise KronicleConnectionError(f"Failed to connect to {url}") from last_exc

    def _invalidate_cache(self):
        self._metadata_cache = None

    @classmethod
    def _ensure_is_payload(cls, res) -> KroniclePayload:
        """Ensure the result is a KroniclePayload."""
        if isinstance(res, KroniclePayload):
            return res
        raise TypeError(f"KroniclePayload expected, got '{get_type(res)}' for {res}")

    @classmethod
    def _ensure_is_payload_or_none(cls, res) -> KroniclePayload | None:
        """Ensure the result is a KroniclePayload or None."""
        return None if not res else cls._ensure_is_payload(res)

    @classmethod
    def _ensure_is_payload_list(cls, res) -> list[KroniclePayload]:
        """Ensure the result is a list of KroniclePayload."""
        if not isinstance(res, list):
            raise TypeError(f"List expected, got '{get_type(res)}' for {res}")
        for res_i in res:
            if not isinstance(res_i, KroniclePayload):
                raise TypeError(
                    f"Each element of the list should be a KroniclePayload, got '{get_type(res_i)}' for {res_i}"
                )
        return res

    def _ensure_body_as_payload(self, body: KroniclePayload | dict):
        return body if isinstance(body, KroniclePayload) else KroniclePayload.from_json(body)

    def _ensure_payload_id(self, body: KroniclePayload | dict):
        payload = self._ensure_body_as_payload(body)
        if not (sensor_id := payload.sensor_id):
            raise ValueError("Sensor ID missing")
        return check_is_uuid4(sensor_id)

    # ------------------------------------------------------------------------------------------------------------------
    # HTTP verbs
    # ------------------------------------------------------------------------------------------------------------------

    def get(self, route: str | None = None, **params) -> KroniclePayload | list[KroniclePayload]:
        """Perform a GET request and return validated payload(s)."""
        return self._request(get, route=route, **params)

    def post(
        self, route: str | None = None, body: KroniclePayload | dict | None = None, **params
    ) -> KroniclePayload | list[KroniclePayload]:
        """Perform a POST request with validation."""
        self._invalidate_cache()
        return self._request(post, route=route, body=body, **params)

    def put(self, route: str, body: KroniclePayload | dict, **params) -> KroniclePayload | list[KroniclePayload]:
        """Perform a PUT request with validation."""
        if not body:
            raise ValueError("Please provide a body for this request")
        self._invalidate_cache()
        return self._request(put, route=route, body=body, **params)

    def patch(self, route: str, body: KroniclePayload | dict, **params) -> KroniclePayload | list[KroniclePayload]:
        """Perform a PUT request with validation."""
        if not body:
            raise ValueError("Please provide a body for this request")
        self._invalidate_cache()
        return self._request(patch, route=route, body=body, **params)

    def delete(self, route: str, **params) -> KroniclePayload | list[KroniclePayload]:
        """Perform a DELETE request and return validated payload(s)."""
        self._invalidate_cache()
        return self._request(delete, route=route, **params)

    # ------------------------------------------------------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------------------------------------------------------
    def is_alive(self):
        res = self._parse(get(url=slash_join(self.url, "/health/live")), strict=False)
        return isinstance(res, dict) and res.get("status") == "alive"

    def is_ready(self):
        res = self._parse(get(url=slash_join(self.url, "/health/ready")), strict=False)
        return isinstance(res, dict) and res.get("status") == "ready"

    # ------------------------------------------------------------------------------------------------------------------
    # Convenience API
    # ------------------------------------------------------------------------------------------------------------------

    def get_all_channels(self) -> list[KroniclePayload]:
        """Retrieve all channels as a list of KroniclePayload."""
        return self._ensure_is_payload_list(self.get(route="channels"))

    @property
    def all_channels(self) -> list[KroniclePayload]:
        """Return all channels."""
        if not hasattr(self, "_metadata_cache") or self._metadata_cache is None:
            self._metadata_cache = self.get_all_channels()
        return self._metadata_cache

    @property
    def all_ids(self) -> list:
        """Return all sensor IDs for existing channels."""
        return [channel.sensor_id for channel in self.all_channels]

    def get_channel(self, id: UUID | str) -> KroniclePayload | None:
        """Retrieve a channel by its sensor_id."""
        return self._ensure_is_payload_or_none(self.get(route=f"channels/{check_is_uuid4(id)}"))

    def get_channel_by_sensor_name(self, sensor_name):
        """
        Retrieve the first channel matching a sensor_name.

        Returns:
            KroniclePayload if found, else None.
        """
        for channel in self.all_channels:
            if channel.sensor_name == sensor_name:
                return channel
        log_d("get_channel_by_sensor_name", "Could not found any channel with name", sensor_name)
        return

    def get_channel_with_max_rows(self) -> Tuple[UUID | None, int | None]:
        max_available_rows = 0
        channel_id = None
        for channel in self.all_channels:
            if channel.available_rows > max_available_rows:
                max_available_rows = channel.available_rows
                channel_id = channel.sensor_id
        if max_available_rows > 0:
            return channel_id, max_available_rows
        return None, None

    def get_rows_for_channel(
        self, id: UUID | str, return_type: Literal["str", "df", "dict", "list"] = "list"
    ) -> str | list[dict[str, Any]] | DataFrame | None:
        """
        Retrieve the rows of a channel in specified format.

        Args:
            return_type: 'dict' returns raw rows, 'df' returns pandas DataFrame, 'str' returns string repr.
        """
        result = self._ensure_is_payload(self.get(route=f"channels/{check_is_uuid4(id)}/rows"))
        match return_type:
            case "str":
                return str(result.rows)
            case "df":
                return result.data_frame
            case "list" | "dict":
                return result.rows
        raise ValueError(f"Unexpected value for return_type parameter : {return_type}")

    def get_cols_for_channel(self, id: UUID | str, return_type: Literal["str", "df", "dict", "list"] = "dict"):
        """
        Retrieve the columns of a channel in specified format.

        Args:
            return_type: 'dict' returns raw columns, 'df' returns pandas DataFrame, 'str' returns string repr.
        """
        result = self.get(route=f"channels/{check_is_uuid4(id)}/columns")
        assert isinstance(result, KroniclePayload)

        match return_type:
            case "str":
                return str(result.columns)
            case "df":
                return result.data_frame
            case "dict" | "list":
                return result.columns
        raise ValueError(f"Unexpected value for return_type parameter : {return_type}")


if __name__ == "__main__":
    here = "abstract Kronicle connector"
    log_d(here)
    try:
        kronicle = KronicleAbstractConnector("http://127.0.0.1:8000")  # type: ignore
    except TypeError as e:
        log_w(here, "WARNING", e)
    log_d(here, "^^^ There should be a warning above ^^^")
