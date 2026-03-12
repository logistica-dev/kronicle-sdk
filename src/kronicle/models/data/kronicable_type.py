# kronicle/models/kronicable_type.py
"""
Defines KronicableTypeChecker which encapsulates the rules for which Python types
are valid as Kronicable fields (for Kronicle metrics) and converts them to
server-compatible type strings.
"""

from datetime import datetime
from types import MappingProxyType, NoneType, UnionType
from typing import Any, Final, Union, get_args, get_origin

from pydantic import BaseModel

from kronicle.models.iso_datetime import IsoDateTime
from kronicle.utils.log import log_w

COL_TO_PY_TYPE: Final = MappingProxyType(
    {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "datetime": datetime,  # custom subclass of datetime
        "dict": dict,
        "list": list,
    }
)
STR_TYPES: Final = set(COL_TO_PY_TYPE.keys())

EXT_COL_TO_PY_TYPE = COL_TO_PY_TYPE.copy()
EXT_COL_TO_PY_TYPE["IsoDateTime"] = IsoDateTime

EXT_STR_TYPES = set(EXT_COL_TO_PY_TYPE.keys())
PRIMITIVE_TYPES: Final = tuple(EXT_COL_TO_PY_TYPE.values())


class KronicableTypeChecker:
    """
    Validates Python type annotations or type strings as Kronicable types
    for KroniclePayload schemas.

    A type is considered "Kronicable" if it belongs to one of the following:
        - a supported primitive type (str, int, float, bool, datetime, dict, list)
        - a Pydantic BaseModel subclass
        - list[T] or dict[str, T] where T is Kronicable
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
        self.optional = False

        # --- Handle string annotation ---
        if isinstance(annotation, str):
            if annotation.startswith("optional[") and annotation.endswith("]"):
                inner_str = annotation[9:-1]
                if inner_str not in EXT_STR_TYPES:
                    raise TypeError(f"Invalid type string: {annotation}")
                self.annotation = EXT_COL_TO_PY_TYPE[inner_str]
                self.optional = True
            elif annotation in EXT_STR_TYPES:
                self.annotation = EXT_COL_TO_PY_TYPE[annotation]
            else:
                raise TypeError(f"Invalid type string: {annotation}")
        else:
            self.annotation = annotation

    # ----------------------------------------------------
    # Classification helpers
    # ----------------------------------------------------
    def is_optional(self) -> bool:
        """
        Return True if the annotation is Optional[T], meaning Union[T, NoneType].
        """
        if self.optional:
            return True
        origin = get_origin(self.annotation)
        if origin in (Union, UnionType):
            self.optional = NoneType in get_args(self.annotation)
        return self.optional

    @property
    def inner_optional(self):
        """
        Return the inner non-None types from an Optional[T] annotation.
        Should return exactly one element for a valid Optional.
        """
        # ---- string-based optional like "optional[int]"
        if self.optional and get_origin(self.annotation) is None:
            return self.annotation

        # ---- union-based optionals
        args = [a for a in get_args(self.annotation) if a is not type(None)]
        if len(args) != 1:
            raise TypeError(
                f"Optional annotation '{self.annotation}' must contain exactly one non-None type (not {len(args)})"
            )
        return args[0]

    def is_primitive(self) -> bool:
        """Return True if the type is a supported primitive."""
        typ = self.inner_optional if self.is_optional() else self.annotation
        return isinstance(typ, type) and issubclass(typ, PRIMITIVE_TYPES)

    def is_basemodel(self) -> bool:
        """Return True if the annotation is a subclass of Pydantic BaseModel."""
        return isinstance(self.annotation, type) and issubclass(self.annotation, BaseModel)

    def is_valid_list(self) -> bool:
        """
        Return True if the annotation is list[T] where T is a BaseModel subclass
        or any primitive type defined in PRIMITIVE_TYPES.
        """
        origin = get_origin(self.annotation)
        args = get_args(self.annotation)
        if origin is list and len(args) == 1 and isinstance(args[0], type):
            return KronicableTypeChecker(args[0]).is_valid()
        return False

    def is_valid_dict(self) -> bool:
        """
        Return True if the annotation is dict[str, T] where T is a BaseModel subclass
        or any primitive type defined in PRIMITIVE_TYPES.
        """
        origin = get_origin(self.annotation)
        args = get_args(self.annotation)
        if origin is dict and len(args) == 2 and args[0] is str and isinstance(args[1], type):
            return KronicableTypeChecker(args[1]).is_valid()
        return False

    # ----------------------------------------------------
    # Main rule: "Is this type acceptable for a Kronicable Sample?"
    # ----------------------------------------------------
    def is_valid(self) -> bool:
        """
        Return True if the annotation is a valid Kronicable type according to
        Kronicle rules: primitives, BaseModels, lists/dicts of BaseModels,
        or Optional variants of the above.
        """
        # Optional[T] -> validate inner T
        if self.is_optional():
            try:
                return KronicableTypeChecker(self.inner_optional).is_valid()
            except Exception as e:
                log_w("KTChecker.is_valid", e)
                return False
        return self.is_primitive() or self.is_basemodel() or self.is_valid_list() or self.is_valid_dict()

    def to_kronicle_type(self) -> str:
        """
        Return the corresponding Kronicle type string for this annotation.
        Raises TypeError if the type is not valid for Kronicable.
        """
        if not self.is_valid():
            raise TypeError(f"Type {self.annotation} is not Kronicable")

        # unwrap Optional[T]
        if self.is_optional():
            inner_type = KronicableTypeChecker(self.inner_optional)
            return f"optional[{inner_type.to_kronicle_type()}]"

        typ = self.annotation

        # primitives
        for k, v in COL_TO_PY_TYPE.items():
            if isinstance(typ, type) and issubclass(typ, v):
                return k

        # generic dict/list -> map to "dict" / "list"
        origin = get_origin(typ)
        if origin is dict:
            return "dict"
        if origin is list:
            return "list"

        # BaseModel subclasses -> serialize as JSON string -> "str"
        if isinstance(typ, type) and issubclass(typ, BaseModel):
            return "str"

        # fallback
        return "str"

    # ----------------------------------------------------------------------------------------------
    # Human-friendly error message
    # ----------------------------------------------------------------------------------------------
    def describe(self) -> str:
        """
        Return a human-friendly string describing the annotation.
        Useful for error messages.
        """
        return str(self.annotation)

    @classmethod
    def str_to_py_type_map(cls) -> dict:
        return dict(COL_TO_PY_TYPE.items())

    @classmethod
    def py_to_str_type_map(cls) -> dict:
        return {val: key for key, val in COL_TO_PY_TYPE.items()}


# --------------------------------------------------------------------------------------------------
# Example usage
# --------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    from typing import Optional

    here = "test"
    print("\n=== KronicableTypeChecker test ===")

    def print_kronicable(t: str | type | Union[Any, Any], t_name: str | None = None):
        if not t_name:
            try:
                t_name = t.__name__  # type:ignore
            except AttributeError:
                t_name = str(t)
        kt = KronicableTypeChecker(t)
        is_valid = kt.is_valid()
        print(
            "{:<15}->".format(t_name),
            f"kronicable: {kt.to_kronicle_type()}" if is_valid else "n/a",
        )

    # --- Primitive tests ------------------------------------------------------
    for t in (int, float, str, bool, datetime, "int", "float", "str", "bool", "datetime"):
        print_kronicable(t)

    # --- Inheriting primitive tests -------------------------------------------
    print_kronicable(IsoDateTime)

    # --- BaseModel tests ------------------------------------------------------
    class Sub(BaseModel):
        x: int

    print_kronicable(Sub, "Sub(BaseModel)")

    # --- Optional primitive ---------------------------------------------------
    print_kronicable("optional[int]", "Optional[int]")
    print_kronicable(Optional[int], "Optional[int]")
    print_kronicable(Optional[Sub], "Optional[Sub]")
    print_kronicable(str | None, "str | None")
    print_kronicable(Sub | None, "Sub | None")

    # --- list ------------------------------------------------------
    print_kronicable(list, "list")
    print_kronicable(list[str], "list[str]")
    print_kronicable(list[int], "list[int]")
    print_kronicable(list[Sub], "list[Sub]")

    # --- dict[str, BaseModel] -------------------------------------------------
    print_kronicable(dict, "dict")
    print_kronicable(dict[str, int], "dict[str, int]")
    print_kronicable(dict[str, Sub], "dict[str, Sub]")

    # --- invalid types ---------------------------------------------------------
    print("\n=== Not allowed ===\n")

    class NotAllowed:
        pass

    print_kronicable(Optional, "Optional")  # type: ignore
    print_kronicable(list[Any], "list[Any]")
    print_kronicable(dict[str, Any], "dict[str, Any]")
    print_kronicable(Sub | str, "Sub | str")
    print_kronicable(str | int | None, "str | int | None")
    print_kronicable(NotAllowed)

    print("\n=== Done ===\n")
