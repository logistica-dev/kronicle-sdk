# kronicle_sdk/models/data/kronicable_flat_sample.py
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel

from kronicle_sdk.models.data.kronicable_sample import KronicableSample
from kronicle_sdk.models.data.kronicable_type import KronicableTypeChecker


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


if __name__ == "__main__":  # pragma: no-cover
    pass
