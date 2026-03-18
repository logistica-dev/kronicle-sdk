# kronicle/connectors/channel/abc_channel_connector.py
from abc import abstractmethod
from typing import Any, Callable, Literal, Tuple
from uuid import UUID

from requests import Response, delete, get, patch, post, put

from kronicle_sdk.connectors.auth.kronicle_auth import KronicleUsrLogin
from kronicle_sdk.models.data.kronicle_payload import KroniclePayload
from kronicle_sdk.models.kronicle_errors import KronicleResponseError
from kronicle_sdk.utils.log import log_d, log_w
from kronicle_sdk.utils.str_utils import check_is_uuid4, get_type


class KronicleAbstractChannelConnector(KronicleUsrLogin):
    """
    Abstract class that implements generic connection
    methods towards Kronicle.

    Args:
    url: Base URL of the Kronicle server.
    """

    def __init__(self, url: str, usr: str, pwd: str):
        super().__init__(url, usr, pwd)

    @property
    @abstractmethod
    def prefix(self) -> str:
        raise NotImplementedError("Define a route prefix such as 'api/v1', 'data/v1', or 'setup/v1'.")

    # ----------------------------------------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------------------------------------

    def _parse(self, response: Response, *, strict=True, **params) -> KroniclePayload | list[KroniclePayload]:
        """
        Parse a requests.Response object into validated KroniclePayload(s).

        Raises:
            KronicleResponseError: If the response is invalid or not JSON.
        """
        data = super()._parse(response)
        if not strict:
            return data
        try:
            if isinstance(data, dict):
                return KroniclePayload.from_json(data)
            if isinstance(data, list):
                return [KroniclePayload.from_json(d) for d in data]
        except Exception as exc:
            raise KronicleResponseError(
                "Unexpected response format. Expected KroniclePayload or list[KroniclePayload], got:"
                f" {response.content}"
            ) from exc

        raise KronicleResponseError(f"Unexpected response type: {get_type(data)}; expected dict or list")

    def _request(
        self,
        method: Callable,
        route: str | None = None,
        body: KroniclePayload | dict | None = None,
        *,
        strict: bool = True,
        should_log: bool = False,
        **params,
    ) -> KroniclePayload | list[KroniclePayload]:
        return super()._request(method=method, route=route, body=body, strict=strict, should_log=should_log, **params)

    def _invalidate_cache(self):
        self._metadata_cache = None

    def _serialize_payload(self, body) -> dict | None:
        if body is None:
            return None
        if isinstance(body, KroniclePayload):
            payload = body
        elif isinstance(body, dict):
            payload = KroniclePayload.from_json(body)
        else:
            raise TypeError(f"Invalid body type: {get_type(body)}")
        return payload.model_dump(mode="json", exclude_none=True)

    # ----------------------------------------------------------------------------------------------
    # HTTP verbs
    # ----------------------------------------------------------------------------------------------

    def get(self, route: str | None = None, **params) -> KroniclePayload | list[KroniclePayload]:
        """Perform a GET request and return validated payload(s)."""
        return self._request(get, route=route, **params)

    def post(
        self, route: str | None = None, body: KroniclePayload | dict | None = None, **params
    ) -> KroniclePayload | list[KroniclePayload]:
        """Perform a POST request with validation."""
        return self._request(post, route=route, body=body, **params)

    def put(self, route: str, body: KroniclePayload | dict, **params) -> KroniclePayload | list[KroniclePayload]:
        """Perform a PUT request with validation."""
        if not body:
            raise ValueError("Please provide a body for this request")
        return self._request(put, route=route, body=body, **params)

    def patch(self, route: str, body: KroniclePayload | dict, **params) -> KroniclePayload | list[KroniclePayload]:
        """Perform a PUT request with validation."""
        if not body:
            raise ValueError("Please provide a body for this request")
        return self._request(patch, route=route, body=body, **params)

    def delete(self, route: str, **params) -> KroniclePayload | list[KroniclePayload]:
        """Perform a DELETE request and return validated payload(s)."""
        return self._request(delete, route=route, **params)

    # ----------------------------------------------------------------------------------------------
    # Convenience API
    # ----------------------------------------------------------------------------------------------

    def get_all_channels(self, **params) -> list[KroniclePayload]:
        """Retrieve all channels as a list of KroniclePayload."""
        return self._ensure_is_payload_list(self.get(route="channels", **params))

    @property
    def all_channels(self) -> list[KroniclePayload]:
        """Return all channels."""
        if not hasattr(self, "_metadata_cache") or self._metadata_cache is None:
            self._metadata_cache = self.get_all_channels()
        return self._metadata_cache

    @property
    def all_ids(self) -> list:
        """Return all channel IDs for existing channels."""
        return [channel.channel_id for channel in self.all_channels]

    def get_channel(self, id: UUID | str) -> KroniclePayload | None:
        """Retrieve a channel by its channel_id."""
        return self._ensure_is_payload_or_none(self.get(route=f"channels/{check_is_uuid4(id)}"))

    def get_channel_by_channel_name(self, channel_name):
        """
        Retrieve the first channel matching a channel_name.

        Returns:
            KroniclePayload if found, else None.
        """
        for channel in self.all_channels:
            if channel.channel_name == channel_name:
                return channel
        log_d("get_channel_by_channel_name", "Could not found any channel with name", channel_name)
        return

    def get_channel_with_max_rows(self) -> Tuple[UUID | None, int | None]:
        max_available_rows = 0
        channel_id = None
        for channel in self.all_channels:
            if channel.available_rows and channel.available_rows > max_available_rows:
                max_available_rows = channel.available_rows
                channel_id = channel.channel_id
        if max_available_rows > 0:
            return channel_id, max_available_rows
        return None, None

    def get_rows_for_channel(
        self, id: UUID | str, return_type: Literal["str", "dict", "list"] = "list"
    ) -> str | list[dict[str, Any]] | None:
        """
        Retrieve the rows of a channel in specified format.

        Args:
            return_type: 'dict' returns raw rows, 'str' returns string repr.
        """
        result = self._ensure_is_payload(self.get(route=f"channels/{check_is_uuid4(id)}/rows"))
        match return_type:
            case "str":
                return str(result.rows)
            case "list" | "dict":
                return result.rows
        raise ValueError(f"Unexpected value for return_type parameter : {return_type}")

    def get_cols_for_channel(self, id: UUID | str, return_type: Literal["str", "dict", "list"] = "dict"):
        """
        Retrieve the columns of a channel in specified format.

        Args:
            return_type: 'dict' returns raw columns, 'str' returns string repr.
        """
        result = self.get(route=f"channels/{check_is_uuid4(id)}/columns")
        assert isinstance(result, KroniclePayload)

        match return_type:
            case "str":
                return str(result.columns)
            case "dict" | "list":
                return result.columns
        raise ValueError(f"Unexpected value for return_type parameter : {return_type}")


if __name__ == "__main__":  # pragma: no-cover
    here = "abstract Kronicle connector"
    log_d(here)
    try:
        kronicle = KronicleAbstractChannelConnector("http://127.0.0.1:8000")  # type: ignore
    except TypeError as e:
        log_w(here, "WARNING", e)
    log_d(here, "^^^ There should be a warning above ^^^")
