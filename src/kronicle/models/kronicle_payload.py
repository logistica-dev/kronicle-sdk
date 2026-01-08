# kronicle/models/kronicle_payload.py
"""
KroniclePayload: central Data Transfer Object for Kronicle SDK.

Delegates all type validation/normalization to KronicableTypeChecker.
Allows users to provide `channel_schema` as either:
    - dict[str, str] (server-ready strings)
    - dict[str, Python type | Optional[type]] (auto-normalized)
"""
from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from pandas import DataFrame, DatetimeIndex, read_csv, to_datetime
from pydantic import BaseModel, field_validator, model_validator

from kronicle.models.iso_datetime import IsoDateTime, now_local, now_utc
from kronicle.models.kronicable_type import STR_TYPES, KronicableTypeChecker
from kronicle.utils.log import log_d

mod = "KroniclePayload"


class KroniclePayload(BaseModel):
    """
    Data transfer object for any response or request to the Kronicle.

    This structure centralizes all data that can be returned by the API for a
    channel, including metadata, tags, data rows, and column-oriented data.

    Fields
    ------
    channel_id : UUID | None
        Unique identifier of the channel.
    channel_schema : dict[str, str] | None
        A dictionary mapping column names to type names (str, int, float, ...).
        Validated against a fixed set of allowed type labels.
    channel_name : str | None
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

    channel_id: UUID | None = None
    channel_schema: dict[str, str] | None = None
    channel_name: str | None = None
    metadata: dict[str, Any] | None = None
    tags: dict[str, str | int | float | bool | list | datetime] | None = None
    rows: list[dict[str, Any]] | None = None
    columns: dict[str, list] | None = None
    received_at: IsoDateTime | None = None
    available_data: int | None = None
    op_status: str | None = None
    op_details: dict[str, Any] | None = None
    available_rows: int | None = None

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
    def from_json(cls, payload: dict):
        """
        Create a KroniclePayload from a Python dict
        (JS-style convenience wrapper around `model_validate`, which you may use instead).
        """
        if schema := payload.get("channel_schema"):
            normalized = {}
            for col, typ in schema.items():
                kt = KronicableTypeChecker(typ)
                normalized[col] = kt.to_kronicle_type()
            payload["channel_schema"] = normalized
        return cls.model_validate(payload)

    @classmethod
    def from_str(cls, payload: str):
        """Create a KroniclePayload from a JSON string."""
        return cls.model_validate_json(payload)

    # ----------------------------------------------------------------------------------------------
    # Serialization helpers
    # ----------------------------------------------------------------------------------------------
    def to_json(self, **args) -> dict:
        """Convert to a Python dict"""
        return super().model_dump(**args)

    def model_dump(self, **args) -> dict:
        """Convert to a Python dict"""
        return super().model_dump(**args)

    def model_dump_json(self, indent: int | None = 2, **args) -> str:
        """Convert to a JSON string"""
        return super().model_dump_json(indent=indent, **args)

    def to_json_str(self, indent: int | None = 2, **args) -> str:
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
        if self.channel_id:
            return self.channel_id
        raise ValueError("Channel ID missing")

    def get_columns(self):
        return self.columns if self.columns else self._rows_to_columns()

    @property
    def data_frame(self) -> DataFrame | None:
        """
        Convert `columns` into a pandas.DataFrame.

        Datetime columns (according to `channel_schema`) are converted to UTC
        to ensure compatibility with pandas' datetime64[ns, UTC] dtype.

        Returns
        -------
        DataFrame | None
            A DataFrame where each key of `columns` becomes a column.
            The "time" column, if present, is used as DatetimeIndex.

        Raises
        ------
        ValueError
            If column lengths are inconsistent or datetime conversion fails.
        TypeError
            If `columns` is not a dict of lists.
        """
        if self.get_columns() is None:
            log_d("KroniclePayload.data_frame", "no columns found for", self)
            return None

        if not isinstance(self.columns, dict):
            raise TypeError("Columns must be a dict of lists")

        # Validate all columns are lists and have same length
        lengths = {len(v) for v in self.columns.values() if isinstance(v, list)}
        if len(lengths) > 1:
            raise ValueError(f"Column lists have inconsistent lengths: {lengths}")

        df = DataFrame(self.columns)

        # Convert datetime columns to UTC
        if self.channel_schema:
            datetime_cols = [col for col, typ in self.channel_schema.items() if typ == "datetime"]
            for col in datetime_cols:
                if col in df.columns:
                    df[col] = to_datetime(df[col], utc=True)

        # Special handling for "time" -> datetime index
        if "time" in df.columns:
            try:
                df.index = DatetimeIndex(df["time"])
                df = df.drop(columns=["time"])
            except Exception as e:
                raise ValueError(f"Failed to interpret 'time' column as datetime: {e}") from e

        return df

    def to_csv(self, path: str | None = None, **kwargs) -> str | None:
        """Return CSV string or save to file if path is given."""
        df = self.data_frame
        if df is None:
            return None
        if path:
            df.to_csv(path, **kwargs)
            return None
        return df.to_csv(**kwargs)

    @classmethod
    def from_csv(cls, csv_path: str, **kwargs) -> "KroniclePayload":
        """Load columns from a CSV file and build a KroniclePayload."""
        df = read_csv(csv_path, **kwargs)
        return cls(columns={col: df[col].tolist() for col in df.columns})


if __name__ == "__main__":
    from kronicle.utils.str_utils import tiny_id, uuid4_str

    here = "Kronicle payload"

    now1 = now_local()
    now2 = now_utc()
    payload_dict = {
        "channel_id": uuid4_str(),
        "channel_name": "temperature_channel",
        "channel_schema": {"time": "IsoDateTime", "temperature": "float", "pressure": "optional[float]"},
        "metadata": {"unit": "C"},
        "tags": {"test": True},
        "rows": [
            {"time": now1, "temperature": 21.5},
            {"time": now2, "temperature": 22.3},
        ],
        "columns": {
            "time": [now1, now2],
            "temperature": [21.5, 22.3],
        },
        "received_at": now_local(),
        "available_data": 2,
        "op_status": "success",
        "op_details": {"issued_at": now_local()},
    }

    log_d(here, "=== Creating KroniclePayload from dict ===")
    payload = KroniclePayload.from_json(payload_dict)
    log_d(here, payload)

    log_d(here, "=== Accessing data_frame property ===")
    df = payload.data_frame
    log_d(here, df)

    log_d(here, "=== Serializing back to JSON ===")
    json_str = payload.model_dump_json()
    log_d(here, json_str)

    log_d(here, "=== Creating KroniclePayload from JSON string ===")
    payload_from_str = KroniclePayload.from_str(json_str)
    log_d(here, payload_from_str)

    log_d(here, "=== Checking validation ===")
    try:
        bad_payload = KroniclePayload(channel_schema={"time": "datetime", "temp": "unknown_type"})
    except ValueError as e:
        log_d(here, "Caught expected validation error:", e)

    payload_dict = {
        "channel_id": uuid4_str(),
        "channel_name": "temperature_channel",
        "channel_schema": {
            "time": "datetime",
            "temperature": float,  # Python type auto-normalized
            "pressure": KronicableTypeChecker(float).to_kronicle_type(),  # can also wrap
        },
        "metadata": {"unit": "C"},
        "tags": {"test": True},
        "rows": [{"time": now_local(), "temperature": 21.5}],
        "columns": {"time": [now_local()], "temperature": [21.5]},
        "received_at": now_local(),
        "available_data": 1,
        "op_status": "success",
        "op_details": {"issued_at": now_local()},
    }

    log_d(here, "=== Creating KroniclePayload from dict ===")
    payload = KroniclePayload.from_json(payload_dict)
    log_d(here, payload)

    log_d(here, "=== Accessing data_frame property ===")
    df = payload.data_frame
    log_d(here, df)

    log_d(here, "=== Serializing back to JSON ===")
    json_str = payload.model_dump_json()
    log_d(here, json_str)

    log_d(here, "=== Creating KroniclePayload from JSON string ===")
    payload_from_str = KroniclePayload.from_str(json_str)
    log_d(here, payload_from_str)

    log_d(here, "=== Checking validation ===")
    try:
        bad_payload = KroniclePayload(channel_schema={"time": "datetime", "temp": "unknown_type"})
    except ValueError as e:
        log_d(here, "Caught expected validation error:", e)

    channel_id = uuid4_str()
    channel_name = f"demo_channel_{tiny_id()}"
    now_tag = now_local()

    payload = {
        "channel_id": channel_id,
        "channel_name": channel_name,
        "channel_schema": {"time": datetime, "temperature": float},
        "metadata": {"unit": "°C"},
        "tags": {"test": now_tag},
        "rows": [
            {"time": "2025-01-01T00:00:00Z", "temperature": 12.3},
            {"time": "2025-01-01T00:01:00Z", "temperature": 12.8},
        ],
    }

    log_d(here, "=== Creating KroniclePayload from dict ===")
    kp = KroniclePayload.from_json(payload=payload)
    log_d(here, kp)
