# kronicle/models/kronicable_sample.py
from json import dumps
from typing import Any

from pydantic import BaseModel, PrivateAttr, computed_field, model_validator

from kronicle_sdk.models.data.kronicable_type import COL_TO_PY_TYPE, KronicableTypeChecker
from kronicle_sdk.models.iso_datetime import IsoDateTime, now


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

    _hidden_field: str = PrivateAttr(default="If you need a hidden field, this is the way to declare it")

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
    # Methods to generate KroniclePayload
    # ----------------------------------------------------------------------------------------------
    @classmethod
    def get_all_fields(cls):
        return {**cls.model_fields, **cls.model_computed_fields}

    @classmethod
    def _get_channel_schema(cls) -> dict[str, str]:
        schema: dict[str, str] = {}

        # Regular fields:  declared_type = field.annotation
        # Computed fields: declared_type = field.return_type
        for name, field in cls.get_all_fields().items():
            declared_type = field.annotation if hasattr(field, "annotation") else field.return_type
            kt = KronicableTypeChecker(declared_type)
            schema[name] = kt.to_kronicle_type()

        return schema

    @property
    def channel_schema(self) -> dict[str, str]:
        """
        Return a canonical channel schema for the class, including computed fields.
        """
        return self._get_channel_schema()

    @classmethod
    def get_field_descriptions(cls) -> dict[str, str]:
        """
        Return a dict mapping field names to their description, if a description was provided.
        Works safely for both ModelField and FieldInfo.
        """
        descriptions = {}
        for name, field in cls.model_fields.items():
            # If it's a ModelField, grab its field_info; else assume it's already FieldInfo
            info = getattr(field, "field_info", field)
            if info.description is not None:
                descriptions[name] = info.description
        return descriptions

    # ----------------------------------------------------------------------------------------------
    # Row serialization
    # ----------------------------------------------------------------------------------------------
    def to_row(self) -> dict[str, Any]:
        """
        Convert this object into a dictionary for KroniclePayload.
        Nested BaseModel or list/dict of BaseModels is serialized to dict.
        Fields with None values are omitted (optional fields not set).
        """
        row: dict[str, Any] = {}

        for name, field in self.get_all_fields().items():
            value = getattr(self, name)
            field_type = field.annotation if hasattr(field, "annotation") else field.return_type
            kt = KronicableTypeChecker(field_type)

            # Handle None values
            if value is None:
                if kt.is_optional():
                    # Optional field not set -> skip it
                    continue
                else:
                    # Required field is None -> raise error early
                    raise ValueError(f"Field '{name}' is required but has value None")

            if isinstance(value, BaseModel):
                row[name] = value.model_dump()
            elif isinstance(value, list) and value and all(isinstance(v, BaseModel) for v in value):
                row[name] = dumps([v.model_dump() for v in value])
            elif isinstance(value, dict) and value and all(isinstance(v, BaseModel) for v in value.values()):
                row[name] = dumps({k: v.model_dump() for k, v in value.items()})
            else:
                row[name] = value
        return row


# ------------------------------------------------------------
# Example usage
# ------------------------------------------------------------
if __name__ == "__main__":  # pragma: no-cover
    from kronicle_sdk.utils.log import log_d

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
    schema = metrics.channel_schema

    log_d(here, "Channel schema", schema)

    # --- 1. Proper instantiation with optional None ---
    metrics = TransferMetrics(start_time=now(), liste2=[])
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
