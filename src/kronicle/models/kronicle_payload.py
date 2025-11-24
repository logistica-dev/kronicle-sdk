from typing import Any
from uuid import UUID

from pandas import DataFrame, DatetimeIndex, read_csv
from pydantic import BaseModel, field_validator, model_validator

from kronicle.models.iso_datetime import IsoDateTime, now_local, now_utc
from kronicle.utils.log import log_d
from kronicle.utils.str_utils import uuid4_str

COL_TO_PY_TYPE = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "datetime": IsoDateTime,  # custom subclass of datetime
    "dict": dict,
    "list": list,
}
STR_TYPES = COL_TO_PY_TYPE.keys()


class KroniclePayload(BaseModel):
    """
    Data transfer object for any response or request to the Kronicle.

    This structure centralizes all data that can be returned by the API for a
    sensor, including metadata, tags, data rows, and column-oriented data.

    Fields
    ------
    sensor_id : UUID | None
        Unique identifier of the sensor.
    sensor_schema : dict[str, str] | None
        A dictionary mapping column names to type names (str, int, float, ...).
        Validated against a fixed set of allowed type labels.
    sensor_name : str | None
        Human-friendly identifier for the sensor.
    metadata : dict[str, Any] | None
        Arbitrary metadata attached to the sensor.
    tags : dict[str, str | int | float | list] | None
        Tag set used for filtering and grouping sensors.
    rows : list[dict[str, Any]] | None
        Row-oriented data, usually raw samples as received.
    columns : dict[str, list] | None
        Column-oriented data, typically produced by the server for efficient retrieval.
        Each key is a column name; each value is the list of values for that column.
    received_at : IsoDateTime | None
        Timestamp (server-side) for when the payload was created or returned.
    available_data : int | None
        Count or size of available data points for this sensor.
    op_status : str | None
        Operation status returned by write/update operations.
    op_details : dict[str, Any] | None
        Optional details attached to the operation result.
    """

    sensor_id: UUID | None = None
    sensor_schema: dict[str, str] | None = None
    sensor_name: str | None = None
    metadata: dict[str, Any] | None = None
    tags: dict[str, str | int | float | list] | None = None
    rows: list[dict[str, Any]] | None = None
    columns: dict[str, list] | None = None
    received_at: IsoDateTime | None = None
    available_data: int | None = None
    op_status: str | None = None
    op_details: dict[str, Any] | None = None
    available_rows: int = 0

    # ------------------------------------------------------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------------------------------------------------------
    @model_validator(mode="after")
    def _populate_available_rows(self):
        if self.op_details and (available_rows := self.op_details.get("available_rows")):
            self.available_rows = available_rows
        return self

    @field_validator("sensor_schema")
    def _validate_schema(cls, schema):
        """
        Ensure that the schema is a <column_name: column_type> dict with "column_type" containing
        only recognized type labels.
        """
        if schema is None:
            return None
        if not isinstance(schema, dict):
            raise TypeError("sensor_schema must be a dict")

        invalid = {k: v for k, v in schema.items() if v not in STR_TYPES}
        if invalid:
            raise ValueError(f"Invalid schema types {invalid}; allowed: {sorted(STR_TYPES)}")
        return schema

    # ------------------------------------------------------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------------------------------------------------------

    @classmethod
    def from_json(cls, payload: dict):
        """
        Create a KroniclePayload from a Python dict
        (JS-style convenience wrapper around `model_validate`, which you may use instead).
        """
        return cls.model_validate(payload)

    @classmethod
    def from_str(cls, payload: str):
        """Create a KroniclePayload from a JSON string."""
        return cls.model_validate_json(payload)

    # ------------------------------------------------------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------------------------------------------------------
    def model_dump(self, **args) -> dict:
        """Convert to a Python dict"""
        return super().model_dump(**args)

    def model_dump_json(self, indent: int | None = 2, **args) -> str:
        """Convert to a JSON string"""
        return super().model_dump_json(indent=indent, **args)

    def __str__(self) -> str:
        """Convert to a (JSON) string"""
        return self.model_dump_json(indent=2, exclude_none=True)

    # ------------------------------------------------------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------------------------------------------------------
    def ensure_has_id(self) -> UUID:
        if self.sensor_id:
            return self.sensor_id
        raise ValueError("Sensor ID missing")

    @property
    def data_frame(self) -> DataFrame | None:
        """
        Convert `columns` into a pandas.DataFrame.

        Returns
        -------
        DataFrame | None
            A DataFrame where each key of `columns` becomes a column.
            If a column named "time" exists, it is converted into a DatetimeIndex.

        Raises
        ------
        ValueError
            If `columns` has inconsistent column lengths.
        TypeError
            If `columns` is not a mapping of lists.
        """
        if self.columns is None:
            return None

        if not isinstance(self.columns, dict):
            raise TypeError("columns must be a dict of lists")

        # Validate all columns are lists and have same length
        lengths = {len(v) for v in self.columns.values() if isinstance(v, list)}
        if len(lengths) > 1:
            raise ValueError(f"Column lists have inconsistent lengths: {lengths}")

        df = DataFrame(self.columns)

        # Special handling for "time" → datetime index
        if "time" in df.columns:
            try:
                new_index = DatetimeIndex(df["time"])
                df = df.drop(columns=["time"])
                df.index = new_index
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

    here = "Kronicle payload"
    # Example payload
    now1 = now_local()
    now2 = now_utc()
    payload_dict = {
        "sensor_id": uuid4_str(),
        "sensor_name": "temperature_sensor",
        "sensor_schema": {"time": "datetime", "temperature": "float"},
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
        bad_payload = KroniclePayload(sensor_schema={"time": "datetime", "temp": "unknown_type"})
    except ValueError as e:
        log_d(here, "Caught expected validation error:", e)
