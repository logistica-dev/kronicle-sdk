# kronicle/models/kronicle_payload.py
"""
KronicleChannel: central Data Transfer Object for Kronicle SDK.

Delegates all type validation/normalization to KronicableTypeChecker.
Allows users to provide `channel_schema` as either:
    - dict[str, str] (server-ready strings)
    - dict[str, Python type | Optional[type]] (auto-normalized)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import field_validator, model_validator

from kronicle_sdk.models.data.kronicable_type import STR_TYPES, KronicableTypeChecker
from kronicle_sdk.models.iso_datetime import IsoDateTime
from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase
from kronicle_sdk.models.rbac.kronicle_zone import KronicleZone
from kronicle_sdk.utils.str_utils import uuid_to_str

mod = "KronicleChannel"


class KronicleChannel(KronicleRbacBase):
    """
    Data transfer object for any response or request to the Kronicle.

    This structure centralizes all data that can be returned by the API for a
    channel, including metadata, tags, data rows, and column-oriented data.

    Fields
    ------
    id : UUID | None
        Unique identifier of the channel.
    channel_schema : dict[str, str] | None
        A dictionary mapping column names to type names (str, int, float, ...).
        Validated against a fixed set of allowed type labels.
    name : str | None
        Human-friendly identifier for the channel.
    metadata : dict[str, Any] | None
        Arbitrary metadata attached to the channel.
    tags : dict[str, str | int | float | list] | None
        Tag set used for filtering and grouping channels.
    rows : list[dict[str, Any]] | None
        Row-oriented data, usually raw samples as received.
    columns : dict[str, list] | None
        Column-oriented data, typically produced by the server for efficient retrieval.
        Each key is a column name; each value is the list of values for that column.
    received_at : IsoDateTime | None
        Timestamp (server-side) for when the payload was created or returned.
    available_data : int | None
        Count or size of available data points for this channel.
    op_status : str | None
        Operation status returned by write/update operations.
    op_details : dict[str, Any] | None
        Optional details attached to the operation result.
    """

    channel_schema: dict[str, str] | None = None
    metadata: dict[str, Any] | None = None
    tags: dict[str, str | int | float | bool | list | datetime] | None = None
    rows: list[dict[str, Any]] | None = None
    columns: dict[str, list] | None = None
    received_at: IsoDateTime | None = None
    available_data: int | None = None
    op_status: str | None = None
    op_details: dict[str, Any] | None = None
    available_rows: int | None = None
    zone: KronicleZone | None = None

    # ----------------------------------------------------------------------------------------------
    # Validators
    # ----------------------------------------------------------------------------------------------
    @model_validator(mode="after")
    def _populate_available_rows(self):
        if self.op_details and (available_rows := self.op_details.get("available_rows")):
            self.available_rows = available_rows
        return self

    @field_validator("channel_schema")
    def _validate_schema(cls, schema):
        """
        Ensure that channel_schema is a dict mapping column names to types
        that are valid Kronicable types.
        """
        if schema is None:
            return None
        if not isinstance(schema, dict):
            raise TypeError("channel_schema must be a dict")

        normalized = {}
        invalid = {}

        for col, typ in schema.items():
            try:
                kt = KronicableTypeChecker(typ)
                if not kt.is_valid():
                    invalid[col] = typ
                    continue
                normalized[col] = kt.to_kronicle_type()
            except Exception:
                invalid[col] = typ

        if invalid:
            raise ValueError(f"Invalid schema types {invalid}; allowed: {sorted(STR_TYPES)}")

        return normalized

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, tags):
        """
        Normalize tags to JSON-serializable values.

        - datetime -> ISO8601 UTC string
        - bool/int/float/str/list -> kept as is
        - None -> ignored
        - any other type -> converted to str(value)
        - dictionaries as values are explicitly forbidden (ambiguous)
        """

        if tags is None:
            return None

        normalized_tags = {}

        for key, value in tags.items():
            # ignore null values
            if value is None:
                continue

            # forbid nested mapping (not acceptable by server)
            if isinstance(value, dict):
                raise TypeError(
                    f"Tag '{key}' has value {value!r} which is a dict and is not allowed:",
                    " tag values must be JSON primitives or lists.",
                )

            # datetime -> isoformat
            if isinstance(value, datetime):
                normalized_tags[key] = value.astimezone().isoformat()
                continue

            # JSON-safe primitives or list
            if isinstance(value, (str, int, float, bool, list)):
                normalized_tags[key] = value
                continue

            # fallback: check __str__ exists and is callable
            if hasattr(value, "__str__") and callable(value.__str__):
                normalized_tags[key] = str(value)
            else:
                raise TypeError(
                    f"Tag '{key}' has value {value!r} which cannot be serialized; "
                    "it must be a primitive, list, datetime, or implement __str__."
                )

        return normalized_tags

    # ----------------------------------------------------------------------------------------------
    # Constructors
    # ----------------------------------------------------------------------------------------------
    @classmethod
    def from_json(cls, d: dict) -> KronicleChannel:
        """
        Create a KronicleChannel from a Python dict.
        """
        if schema := d.get("channel_schema"):
            normalized = {}
            for col, typ in schema.items():
                kt = KronicableTypeChecker(typ)
                normalized[col] = kt.to_kronicle_type()
            d["channel_schema"] = normalized

        if channel_id := d.get("channel_id"):
            d["id"] = channel_id
            d.pop("channel_id")

        if zone := d.get("zone"):
            d["zone"] = KronicleZone.from_json(zone)

        return cls.model_validate(d)

    @classmethod
    def from_str(cls, payload: str) -> KronicleChannel:
        """Create a KronicleChannel from a JSON string."""
        return cls.model_validate_json(payload)

    # ----------------------------------------------------------------------------------------------
    # Serialization helpers
    # ----------------------------------------------------------------------------------------------
    def to_json(self, **args) -> dict:
        """Convert to a Python dict."""
        return self.model_dump(**args)

    def model_dump(self, **args) -> dict:
        d = super().model_dump(**args)
        if self.zone:
            d["zone_id"] = uuid_to_str(self.zone.id)
            d["zone_name"] = self.zone.name
        d.pop("zone", None)
        return d

    def to_json_str(self, indent: int | None = None, **args) -> str:
        """Convert to a JSON string"""
        return super().model_dump_json(indent=indent, **args)

    def __str__(self) -> str:
        """Convert to a (JSON) string"""
        return self.model_dump_json(indent=2, exclude_none=True)

    # ----------------------------------------------------------------------------------------------
    # Data helpers
    # ----------------------------------------------------------------------------------------------
    def _rows_to_columns(self) -> dict[str, list[Any]] | None:
        """
        Convert row-oriented data into column-oriented form.
        Example:
            [{"a":1,"b":2}, {"a":3,"b":4}] → {"a":[1,3], "b":[2,4]}
        """
        if not self.rows:
            return None
        cols = defaultdict(list)
        for row in self.rows:
            for k, v in row.items():
                cols[k].append(v)
        self.columns = dict(cols)
        return self.columns

    def ensure_has_id(self) -> UUID:
        if self.id:
            return self.id
        raise ValueError("Channel ID missing")

    def get_columns(self):
        return self.columns if self.columns else self._rows_to_columns()
