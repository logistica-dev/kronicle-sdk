# kronicle/connectors/channel/abc_channel_connector.py
from abc import abstractmethod
from typing import Any, Callable, Literal
from urllib.parse import quote
from uuid import UUID

from requests import Response, delete, get, patch, post, put

from kronicle_sdk.connectors.auth.kronicle_auth import KronicleUsrLogin
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.kronicle_errors import KronicleResponseError
from kronicle_sdk.utils.log import log_d, log_w
from kronicle_sdk.utils.str_utils import check_is_uuid4, get_type, normalize_column_name


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

    def _parse(self, response: Response, *, strict=True, **params) -> KronicleChannel | list[KronicleChannel]:
        """
        Parse a requests.Response object into validated KronicleChannel(s).

        Raises:
            KronicleResponseError: If the response is invalid or not JSON.
        """
        data = super()._parse(response)
        if not strict:
            return data
        try:
            if isinstance(data, dict):
                return KronicleChannel.from_json(data)
            if isinstance(data, list):
                return [KronicleChannel.from_json(d) for d in data]
        except Exception as exc:
            raise KronicleResponseError(
                "Unexpected response format. Expected KronicleChannel or list[KronicleChannel], got:"
                f" {response.content}"
            ) from exc

        raise KronicleResponseError(f"Unexpected response type: {get_type(data)}; expected dict or list")

    def _request(
        self,
        method: Callable,
        route: str | None = None,
        body: KronicleChannel | dict | None = None,
        *,
        strict: bool = True,
        should_log: bool = False,
        params: dict | None = None,
        **kwargs,
    ) -> KronicleChannel | list[KronicleChannel]:
        return super()._request(
            method=method,
            route=route,
            body=body,
            strict=strict,
            should_log=should_log,
            params=params,
            **kwargs,
        )

    def _invalidate_cache(self):
        self._metadata_cache = None

    def _serialize_payload(self, body) -> dict | None:
        if body is None:
            return None
        if isinstance(body, KronicleChannel):
            payload = body
        elif isinstance(body, dict):
            payload = KronicleChannel.from_json(body)
        else:
            raise TypeError(f"Invalid body type: {get_type(body)}")
        return payload.model_dump(mode="json", exclude_none=True)

    # ----------------------------------------------------------------------------------------------
    # HTTP verbs
    # ----------------------------------------------------------------------------------------------

    def get(
        self, route: str | None = None, *, params: dict | None = None, **kwargs
    ) -> KronicleChannel | list[KronicleChannel]:
        """Perform a GET request and return validated payload(s)."""
        return self._request(get, route=route, params=params, **kwargs)

    def post(
        self,
        route: str | None = None,
        body: KronicleChannel | dict | None = None,
        **kwargs,
    ) -> KronicleChannel | list[KronicleChannel]:
        """Perform a POST request with validation."""
        return self._request(post, route=route, body=body, **kwargs)

    def put(self, route: str, body: KronicleChannel | dict, **kwargs) -> KronicleChannel | list[KronicleChannel]:
        """Perform a PUT request with validation."""
        if not body:
            raise ValueError("Please provide a body for this request")
        return self._request(put, route=route, body=body, **kwargs)

    def patch(
        self,
        route: str,
        body: KronicleChannel | dict,
        **kwargs,
    ) -> KronicleChannel | list[KronicleChannel]:
        """Perform a PUT request with validation."""
        if not body:
            raise ValueError("Please provide a body for this request")
        return self._request(patch, route=route, body=body, **kwargs)

    def delete(self, route: str, params: dict | None = None, **kwargs) -> KronicleChannel | list[KronicleChannel]:
        """Perform a DELETE request and return validated payload(s)."""
        return self._request(delete, route=route, params=params, **kwargs)

    # ----------------------------------------------------------------------------------------------
    # Convenience API
    # ----------------------------------------------------------------------------------------------

    def list_channels(self, params: dict | None = None, **kwargs) -> list[KronicleChannel]:
        """Retrieve all channels as a list of KronicleChannel."""
        return self._ensure_is_payload_list(self.get(route="channels", params=params, **kwargs))

    @property
    def all_channels(self) -> list[KronicleChannel]:
        """Return all channels."""
        if not hasattr(self, "_metadata_cache") or self._metadata_cache is None:
            self._metadata_cache = self.list_channels()
        return self._metadata_cache

    @property
    def all_ids(self) -> list:
        """Return all channel IDs for existing channels."""
        return [channel.id for channel in self.all_channels]

    def get_channel(self, id: UUID | str) -> KronicleChannel | None:
        """Retrieve a channel by its channel_id."""
        return self._ensure_is_payload_or_none(self.get(route=f"channels/{check_is_uuid4(id)}"))

    def get_channel_with_name(self, channel_name):
        """
        Retrieve the first channel matching a channel_name.

        Returns:
            KronicleChannel if found, else None.
        """
        res = self.get(route=f"channels/?name={channel_name}", strict=None)
        log_d("get_channel_with_name", res)
        return self._ensure_is_payload_or_none(res)

    def get_channel_with_tags(self, tags: dict[str, str]) -> list[KronicleChannel]:
        """
        Retrieve the channels matching the input tags.

        Returns:
            list[KronicleChannel]
        """
        tags_str = ",".join(f"{normalize_column_name(k)}:{v}" for k, v in tags.items())
        log_d("get_channel_with_tags", "tags_str", tags_str)
        return self._ensure_is_payload_list(self.get(route=f"channels/?tags={quote(tags_str)}"))

    def get_channel_with_meta(self, metadata: dict[str, str]) -> list[KronicleChannel]:
        """
        Retrieve the channels matching the input metadata.

        Returns:
            list[KronicleChannel]
        """
        meta_str = ",".join(f"{normalize_column_name(k)}:{v}" for k, v in metadata.items())
        log_d("get_channel_with_meta", "meta_str", meta_str)
        return self._ensure_is_payload_list(self.get(route=f"channels/?metadata={quote(meta_str)}"))

    def get_channel_with_max_rows(self) -> KronicleChannel | None:
        max_channel = max(self.all_channels, key=lambda chan: chan.available_rows or 0)
        return max_channel

    def get_rows_for_channel(
        self, id: UUID | str, return_type: Literal["str", "dict", "list"] = "list"
    ) -> str | list[dict[str, Any]] | None:
        """
        Retrieve the rows of a channel in specified format.

        Args:
            return_type: 'dict' returns raw rows, 'str' returns string repr.
        """
        here = "get_rows_for_chan"
        log_d(here, "id", id)
        res = self.get(route=f"channels/{check_is_uuid4(id)}/rows")
        log_d(here, "res", res)
        payload = self._ensure_is_payload(res)
        log_d(here, "payload", payload)
        match return_type:
            case "str":
                return str(payload.rows)
            case "list" | "dict":
                return payload.rows
        raise ValueError(f"Unexpected value for return_type parameter : {return_type}")

    def get_cols_for_channel(self, id: UUID | str, return_type: Literal["str", "dict", "list"] = "dict"):
        """
        Retrieve the columns of a channel in specified format.

        Args:
            return_type: 'dict' returns raw columns, 'str' returns string repr.
        """
        result = self.get(route=f"channels/{check_is_uuid4(id)}/columns")
        assert isinstance(result, KronicleChannel)

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
