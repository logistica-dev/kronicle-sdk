# kronicle/models/kronicable_sample.py
from json import dumps
from typing import Any

from pydantic import BaseModel, computed_field, model_validator

from kronicle.models.iso_datetime import IsoDateTime, now
from kronicle.models.kronicable_type import KronicableTypeChecker
from kronicle.models.kronicle_payload import COL_TO_PY_TYPE


class SingleTypeField:
    """Marker for fields that must be a single type (or Optional[type])."""

    pass


ACCEPTABLE_PRIMITIVES = list(COL_TO_PY_TYPE.keys())


class KronicableSample(BaseModel):
    """
    Base class for metrics that can be converted into a KroniclePayload.

    - Ensures that every field (regular or computed) has exactly one type
      or is nullable (Optional[T]) or is a BaseModel/list/dict of BaseModels.
    - Provides `to_row` for automatic payload serialization.
    """

    # ----------------------------------------------------------------------------------------------
    # Validators
    # ----------------------------------------------------------------------------------------------
    @model_validator(mode="before")
    @classmethod
    def _check_field_types(cls, values):
        for name, field in cls.model_fields.items():
            kt = KronicableTypeChecker(field.annotation)
            if not kt.is_valid():
                raise TypeError(f'Field "{name}" has unsupported type for Kronicable: {kt.describe()}')
        return values

    # ----------------------------------------------------------------------------------------------
    # Row serialization
    # ----------------------------------------------------------------------------------------------
    def to_row(self, include_fields: list[str] | None = None) -> dict[str, Any]:
        """
        Convert this object into a dictionary for KroniclePayload.
        Nested BaseModel or list/dict of BaseModels is serialized to JSON.
        Fields with None values are omitted (optional fields not set).
        """
        row: dict[str, Any] = {}
        fields = include_fields if include_fields else self.__dict__.keys()

        for name in fields:
            value = getattr(self, name)
            field_type = self.__class__.model_fields[name].annotation
            kt = KronicableTypeChecker(field_type)

            # Handle None values
            if value is None:
                if kt.is_optional():
                    # Optional field not set → skip it
                    continue
                else:
                    # Required field is None → raise error early
                    raise ValueError(f"Field '{name}' is required but has value None")

            if isinstance(value, BaseModel):
                row[name] = value.model_dump_json()
            elif isinstance(value, list) and all(isinstance(v, BaseModel) for v in value):
                row[name] = dumps([v.model_dump() for v in value])
            elif isinstance(value, dict) and all(isinstance(v, BaseModel) for v in value.values()):
                row[name] = dumps({k: v.model_dump() for k, v in value.items()})
            else:
                row[name] = value
        return row

    # ----------------------------------------------------------------------------------------------
    # Methods to generate KroniclePayload
    # ----------------------------------------------------------------------------------------------
    def get_sensor_schema(self) -> dict[str, str]:
        """
        Return a canonical sensor schema for the class, including computed fields.
        """
        schema: dict[str, str] = {}

        # Regular fields
        for name, field in self.__class__.model_fields.items():
            kt = KronicableTypeChecker(field.annotation)
            schema[name] = kt.to_kronicle_type()

        # Computed fields
        for name, field in self.__class__.model_computed_fields.items():
            kt = KronicableTypeChecker(field.return_type)
            schema[name] = kt.to_kronicle_type()

        return schema


# ------------------------------------------------------------
# Example usage
# ------------------------------------------------------------
if __name__ == "__main__":

    from kronicle.utils.log import log_d

    here = "KronicableSample.tests"

    log_d(here)

    class TransferMetrics(KronicableSample):
        start_time: IsoDateTime
        end_time: IsoDateTime | None = None
        bytes_received: int = 0
        error: str | None = None
        dico: dict[str, KronicableSample] | None = None
        liste: list[KronicableSample] | None = None
        liste2: list[str] | None = None

        @computed_field
        @property
        def success(self) -> bool:
            return self.error is None

    metrics = TransferMetrics(start_time=now(), bytes_received=12345)
    schema = metrics.get_sensor_schema()

    log_d(here, "Sensor schema", schema)

    # --- 1. Proper instantiation with optional None ---
    metrics = TransferMetrics(start_time=now())
    row = metrics.to_row()
    print("Row with optional None fields skipped:", row)
    # Expected: 'end_time' and 'error' should NOT appear in row

    # --- 2. Required field missing (simulate None after instantiation) ---
    try:
        metrics.start_time = None  # required field # type:ignore
        metrics.to_row()
    except ValueError as e:
        print("Caught expected error for required field:", e)

    # --- 3. Fill all fields ---
    metrics.start_time = now()
    metrics.end_time = None
    metrics.error = "Some error"
    row_full = metrics.to_row()
    print("Row with some optional values set:", row_full)
    # Expected: 'end_time' skipped, 'error' included
