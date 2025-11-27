# kronicle/models/kronicable_types.py

from types import MappingProxyType, NoneType, UnionType
from typing import Any, Final, Union, get_args, get_origin

from pydantic import BaseModel

from kronicle.models.iso_datetime import IsoDateTime

COL_TO_PY_TYPE: Final = MappingProxyType(
    {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "datetime": IsoDateTime,  # custom subclass of datetime
        "dict": dict,
        "list": list,
    }
)
STR_TYPES: Final = COL_TO_PY_TYPE.keys()
PRIMITIVE_TYPES: Final = tuple(COL_TO_PY_TYPE.values())
PRIMITIVE_TYPES_STR: Final = list(COL_TO_PY_TYPE.keys())


class KronicableTypeChecker:
    """
    Utility class encapsulating the rules that define whether a Python
    type annotation is valid for usage inside a KronicableSample.

    A type is considered "Kronicable" if it belongs to one of the following:
        - a supported primitive type (str, int, float, bool, datetime, dict, list)
        - a Pydantic BaseModel subclass
        - a list[T] where T is a BaseModel subclass
        - a dict[str, T] where T is a BaseModel subclass
        - Optional[T] where T itself is Kronicable

    This validator is used to ensure that each field in a KronicableSample
    has a compatible type so it can be correctly serialized and pushed into
    a KroniclePayload.
    """

    # Allowed primitives come directly from KroniclePayload's type mapping

    def __init__(self, annotation: Any):
        """
        Store a type annotation (such as int, Optional[str], list[Model], etc.)
        and expose methods to analyze it.
        """
        self.annotation = annotation

    # ----------------------------------------------------
    # Classification helpers
    # ----------------------------------------------------
    def is_optional(self) -> bool:
        """
        Return True if the annotation is Optional[T], meaning Union[T, NoneType].
        """
        typ = self.annotation
        origin = get_origin(typ)
        # args = get_args(typ)
        if origin is Union or origin is UnionType:
            return NoneType in get_args(typ)
        return False

    @property
    def inner_optional(self):
        """
        Return the inner non-None types from an Optional[T] annotation.
        Should return exactly one element for a valid Optional.
        """
        args = [a for a in get_args(self.annotation) if a is not type(None)]
        if len(args) != 1:
            raise TypeError(f"Optional annotation '{self.annotation}' must contain exactly one non-None type")
        return args[0]

    def is_primitive(self) -> bool:
        """Return True if this type is considered primitive."""
        # here = "is_primitive"
        typ = self.annotation

        # Unwrap Optional[T] for the check
        if self.is_optional():
            typ = self.inner_optional

        # Only accept subclasses of types explicitly in PRIMITIVE_TYPES
        if isinstance(typ, type):
            if issubclass(typ, PRIMITIVE_TYPES):
                return True

        return False

    def is_basemodel(self) -> bool:
        """
        Return True if the annotation is a subclass of Pydantic BaseModel.
        """
        return isinstance(self.annotation, type) and issubclass(self.annotation, BaseModel)

    def is_valid_list(self) -> bool:
        """
        Return True if the annotation is list[T] where T is a BaseModel subclass
        or any primitive type defined in PRIMITIVE_TYPES.
        """
        origin = get_origin(self.annotation)
        args = get_args(self.annotation)
        return (
            origin is list
            and len(args) == 1
            and isinstance(t := args[0], type)
            and (issubclass(t, BaseModel) or issubclass(t, PRIMITIVE_TYPES))
        )

    def is_valid_dict(self) -> bool:
        """
        Return True if the annotation is dict[str, T] where T is a BaseModel subclass
        or any primitive type defined in PRIMITIVE_TYPES.
        """
        origin = get_origin(self.annotation)
        args = get_args(self.annotation)
        return (
            origin is dict
            and len(args) == 2
            and args[0] is str
            and isinstance(t := args[1], type)
            and (issubclass(t, BaseModel) or issubclass(t, PRIMITIVE_TYPES))
        )

    # ----------------------------------------------------
    # Main rule: "Is this type acceptable for a Kronicable Sample?"
    # ----------------------------------------------------
    def is_valid(self) -> bool:
        """
        Return True if the annotation is a valid Kronicable type according to
        Kronicle rules: primitives, BaseModels, lists/dicts of BaseModels,
        or Optional variants of the above.
        """
        # Optional[T] → validate inner T
        if self.is_optional():
            inner = self.inner_optional
            return KronicableTypeChecker(inner).is_valid()

        # primitives
        if self.is_primitive():
            return True

        # BaseModel
        if self.is_basemodel():
            return True

        # list/dict of BaseModels
        if self.is_valid_list() or self.is_valid_dict():
            return True

        return False

    def to_kronicle_type(self) -> str:
        """
        Return the corresponding Kronicle type string for this annotation.
        Raises TypeError if the type is not valid for Kronicable.
        """
        if not self.is_valid():
            raise TypeError(f"Type {self.annotation} is not Kronicable")

        typ = self.annotation

        # unwrap Optional[T]
        if self.is_optional():
            typ = self.inner_optional

        # primitives
        for k, v in COL_TO_PY_TYPE.items():
            if isinstance(typ, type) and issubclass(typ, v):
                return k

        # generic dict/list → map to "dict" / "list"
        origin = get_origin(typ)
        if origin is dict:
            return "dict"
        if origin is list:
            return "list"

        # BaseModel subclasses → serialize as JSON string → "str"
        if isinstance(typ, type) and issubclass(typ, BaseModel):
            return "str"

        # fallback
        return "str"

    # ------------------------------------------------------------------------------------------------------------------
    # Human-friendly error message
    # ------------------------------------------------------------------------------------------------------------------
    def describe(self) -> str:
        """
        Return a human-friendly string describing the annotation.
        Useful for error messages.
        """
        return str(self.annotation)


# ----------------------------------------------------------------------------------------------------------------------
# Example usage
# ----------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from datetime import datetime
    from typing import Optional

    from pydantic import BaseModel

    print("\n=== KronicableTypeChecker test ===")

    # --- Primitive tests ------------------------------------------------------
    for t in (int, float, str, bool, datetime):
        kt = KronicableTypeChecker(t)
        print(f"{t.__name__}: valid={kt.is_valid()}")

    # --- Inheriting primitive tests -------------------------------------------
    kt = KronicableTypeChecker(IsoDateTime)
    print(f"{IsoDateTime.__name__}: valid={kt.is_valid()}")

    # --- Optional primitive ---------------------------------------------------
    kt_opt = KronicableTypeChecker(Optional[int])
    print(f"Optional[int]: valid={kt_opt.is_valid()}")

    # --- BaseModel tests ------------------------------------------------------
    class Sub(BaseModel):
        x: int

    kt_sub = KronicableTypeChecker(Sub)
    print(f"Sub(BaseModel): valid={kt_sub.is_valid()}")

    # --- list[BaseModel] ------------------------------------------------------
    kt_list_sub = KronicableTypeChecker(list[Sub])
    print(f"list[Sub]: valid={kt_list_sub.is_valid()}")

    # --- dict[str, BaseModel] -------------------------------------------------
    kt_dict_sub = KronicableTypeChecker(dict[str, Sub])
    print(f"dict[str, Sub]: valid={kt_dict_sub.is_valid()}")

    # --- invalid type ---------------------------------------------------------
    class NotAllowed:
        pass

    kt_bad = KronicableTypeChecker(NotAllowed)
    print(f"NotAllowed: valid={kt_bad.is_valid()}")

    # --- complex nested Optional[list[Sub]] -----------------------------------
    kt_nested = KronicableTypeChecker(Optional[list[Sub]])
    print(f"Optional[list[Sub]]: valid={kt_nested.is_valid()}")

    print("\n=== Done ===\n")
