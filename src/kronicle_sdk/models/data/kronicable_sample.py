# kronicle/models/kronicable_sample.py
from json import dumps
from typing import Any, Union, get_args, get_origin

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


class KronicableFlatSample(KronicableSample):
    """
    A KronicableSample that flattens all one-level BaseModel fields
    into top-level columns for .channel_schema, .to_row(), and .get_field_descriptions().
    """

    # ----------------------------
    # Type unwrapping helper
    # ----------------------------
    @staticmethod
    def _unwrap_type(tp: Any) -> Any:
        """Return the first non-None type inside Optional / Union."""
        origin = get_origin(tp)
        args = get_args(tp)
        if origin is Union and type(None) in args:
            non_none_args = [a for a in args if a is not type(None)]
            if non_none_args:
                return non_none_args[0]
        return tp

    # ----------------------------
    # Flattening helpers
    # ----------------------------
    @classmethod
    def _extract_schema(cls, name: str, declared_type: Any, schema: dict[str, str]):
        declared_type = cls._unwrap_type(declared_type)

        if isinstance(declared_type, type) and issubclass(declared_type, KronicableSample):
            schema.update(declared_type._get_channel_schema())
        elif isinstance(declared_type, type) and issubclass(declared_type, BaseModel):
            for n, f in declared_type.model_fields.items():
                schema[n] = KronicableTypeChecker(f.annotation).to_kronicle_type()
        else:
            schema[name] = KronicableTypeChecker(declared_type).to_kronicle_type()

    @classmethod
    def _extract_descriptions(cls, declared_type: Any, aggregated: dict[str, str]):
        declared_type = cls._unwrap_type(declared_type)

        if isinstance(declared_type, type) and issubclass(declared_type, KronicableSample):
            aggregated.update(declared_type.get_field_descriptions())
        elif isinstance(declared_type, type) and issubclass(declared_type, BaseModel):
            for n, f in declared_type.model_fields.items():
                info = getattr(f, "field_info", f)
                if info.description is not None:
                    aggregated[n] = info.description
        # primitives have no nested descriptions

    @classmethod
    def _extract_row(cls, value: Any, row: dict[str, Any]):
        """Flatten a single value into the row dict, supporting BaseModel, KronicableSample, list/dict of BaseModels."""
        if value is None:
            return
        if isinstance(value, KronicableSample):
            row.update(value.to_row())
        elif isinstance(value, BaseModel):
            row.update(value.model_dump())
        elif isinstance(value, list) and value and all(isinstance(v, BaseModel) for v in value):
            # flatten lists of BaseModels as indexed keys
            for i, v in enumerate(value):
                row.update({f"{i}_{k}": val for k, val in v.model_dump().items()})
        elif isinstance(value, dict) and value and all(isinstance(v, BaseModel) for v in value.values()):
            # flatten dicts of BaseModels
            for k, v in value.items():
                row.update({f"{k}_{fk}": fv for fk, fv in v.model_dump().items()})
        else:
            return value

    # ----------------------------
    # Flattened overrides
    # ----------------------------
    @classmethod
    def _get_channel_schema(cls) -> dict[str, str]:
        schema: dict[str, str] = {}
        for name, field in cls.model_fields.items():
            cls._extract_schema(name, getattr(field, "annotation", Any), schema)
        for name, field in cls.model_computed_fields.items():
            cls._extract_schema(name, getattr(field, "return_type", Any), schema)
        return schema

    @classmethod
    def get_field_descriptions(cls) -> dict[str, str]:
        aggregated: dict[str, str] = {}
        for _, field in cls.model_fields.items():
            cls._extract_descriptions(getattr(field, "annotation", Any), aggregated)
        for _, field in cls.model_computed_fields.items():
            cls._extract_descriptions(getattr(field, "return_type", Any), aggregated)
        return aggregated

    def to_row(self) -> dict[str, Any]:
        row: dict[str, Any] = {}
        for name, _ in self.__class__.model_fields.items():
            extracted = self._extract_row(getattr(self, name), row)
            if extracted is not None:
                row[name] = extracted
        for name, _ in self.__class__.model_computed_fields.items():
            extracted = self._extract_row(getattr(self, name), row)
            if extracted is not None:
                row[name] = extracted
        return row


# ------------------------------------------------------------
# Example usage
# ------------------------------------------------------------
if __name__ == "__main__":  # pragma: no-cover
    from kronicle_sdk.utils.log import log_d

    here = "KronSampl.tests"

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
