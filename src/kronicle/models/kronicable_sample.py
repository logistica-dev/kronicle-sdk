# kronicle/models/kronicle_sample.py

from typing import Union, get_args, get_origin

from pydantic import BaseModel, computed_field, model_validator

from kronicle.models.kronicle_payload import KroniclePayload


class SingleTypeField:
    """Marker for fields that must be a single type (or Optional[type])."""

    pass


class KronicableSample(BaseModel):
    """
    Base class for metrics that can be converted into a KroniclePayload.

    Ensures that every field (regular or computed) has exactly one type
    or is nullable (Optional[T]).
    """

    # ------------------------------------------------------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------------------------------------------------------
    @model_validator(mode="before")
    @classmethod
    def _check_field_types(cls, values):
        # here = "sample._check_field_types"

        for name, field in cls.model_fields.items():
            annotation = field.annotation
            # origin = get_origin(annotation)
            args = get_args(annotation)

            # A field is a union if it has multiple args
            if args:
                # Check for Optional[T]
                if type(None) in args:
                    non_none = [a for a in args if a is not type(None)]
                    if len(non_none) == 1:
                        # Valid: Optional[T]
                        continue

                    # Invalid: Optional[A | B | ...]
                    raise TypeError(
                        f'For the class to be "Kronicable", a property "{name}" may be of type "T | None"'
                        f" with T in {list(KroniclePayload.str_to_py_type_map().keys())}"
                        f" and must not contain multiple types: {annotation}"
                    )

                # Pure union (A | B | ...)
                raise TypeError(
                    f'To be "Kronicable", a property "{name}" must have exactly one type '
                    f" with T in {list(KroniclePayload.str_to_py_type_map().keys())}"
                    f" or be Optional[T], not a union of multiple types: {annotation}"
                )

        return values

    # ------------------------------------------------------------------------------------------------------------------
    # Methods to generate KroniclePayload
    # ------------------------------------------------------------------------------------------------------------------
    def get_sensor_schema(self) -> dict[str, str]:
        """
        Return a canonical sensor schema for the class, including computed fields.
        """
        schema: dict[str, str] = {}
        py_to_str = KroniclePayload.py_to_str_type_map()

        # Regular fields
        for name, field in self.__class__.model_fields.items():
            typ = field.annotation
            # Flatten Optional[T] -> T
            origin = get_origin(typ)
            args = get_args(typ)
            if origin is Union and len(args) == 2 and type(None) in args:
                typ = args[0] if args[1] is type(None) else args[1]

            schema[name] = py_to_str.get(typ, "str")

        # Computed fields
        for name, field in self.__class__.model_computed_fields.items():
            schema[name] = py_to_str.get(field.return_type, "str")

        return schema


# ------------------------------------------------------------
# Example usage
# ------------------------------------------------------------
if __name__ == "__main__":
    from datetime import datetime

    from kronicle.utils.log import log_d

    class TransferMetrics(KronicableSample):
        start_time: datetime
        end_time: datetime | None = None
        bytes_received: int = 0
        error: str | None = None

        @computed_field
        @property
        def success(self) -> bool:
            return self.error is None

    here = "Test KronicableSample"

    metrics = TransferMetrics(start_time=datetime.now(), bytes_received=12345)
    schema = metrics.get_sensor_schema()

    log_d(here, "Sensor schema", schema)
