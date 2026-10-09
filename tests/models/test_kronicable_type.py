# tests/models/test_kronicable_type.py
from datetime import datetime
from typing import Any, Literal, Optional, Union

import pytest
from pydantic import BaseModel, EmailStr

from kronicle_sdk.models.data.kronicable_type import (
    COL_TO_PY_TYPE,
    EXT_STR_TYPES,
    PRIMITIVE_TYPES,
    STR_TYPES,
    KronicableTypeChecker,
)
from kronicle_sdk.models.iso_datetime import IsoDateTime


class Sub(BaseModel):
    x: int = 1


class TestInit:
    def test_plain_string_type(self):
        kt = KronicableTypeChecker("int")
        assert kt.annotation is int
        assert kt.optional is False

    def test_optional_string_type(self):
        kt = KronicableTypeChecker("optional[int]")
        assert kt.annotation is int
        assert kt.optional is True

    def test_invalid_string_raises(self):
        with pytest.raises(TypeError, match="Invalid type string"):
            KronicableTypeChecker("nope")

    def test_optional_invalid_string_raises(self):
        with pytest.raises(TypeError, match="Invalid type string"):
            KronicableTypeChecker("optional[nope]")

    def test_non_string_annotation_stored_as_is(self):
        kt = KronicableTypeChecker(float)
        assert kt.annotation is float
        assert kt.optional is False

    def test_all_known_string_types_accepted(self):
        for name in EXT_STR_TYPES:
            assert KronicableTypeChecker(name).annotation is not None


class TestIsOptional:
    def test_string_optional_short_circuits(self):
        assert KronicableTypeChecker("optional[int]").is_optional() is True

    def test_typing_optional_sets_flag(self):
        kt = KronicableTypeChecker(Optional[int])
        assert kt.is_optional() is True
        assert kt.optional is True

    def test_pep604_optional(self):
        assert KronicableTypeChecker(str | None).is_optional() is True

    def test_union_without_none_is_not_optional(self):
        assert KronicableTypeChecker(Union[int, str]).is_optional() is False

    def test_plain_type_is_not_optional(self):
        assert KronicableTypeChecker(int).is_optional() is False


class TestInnerOptional:
    def test_string_optional_returns_inner(self):
        assert KronicableTypeChecker("optional[int]").inner_optional is int

    def test_union_optional_returns_single_inner(self):
        assert KronicableTypeChecker(Optional[str]).inner_optional is str

    def test_multiple_non_none_values_raise(self):
        kt = KronicableTypeChecker(Optional[Union[int, str]])
        with pytest.raises(TypeError, match="exactly one non-None"):
            _ = kt.inner_optional


class TestUnwrapLiteral:
    def test_uniform_literal_returns_value_type(self):
        kt = KronicableTypeChecker(int)
        assert kt._unwrap_literal(Literal["O", "I"]) is str

    def test_mixed_literal_raises(self):
        kt = KronicableTypeChecker(int)
        with pytest.raises(TypeError, match="mixed types"):
            kt._unwrap_literal(Literal["O", 1])

    def test_non_literal_returned_unchanged(self):
        kt = KronicableTypeChecker(int)
        assert kt._unwrap_literal(int) is int


class TestClassification:
    def test_is_primitive_primitives_and_subclasses(self):
        assert KronicableTypeChecker(int).is_primitive() is True
        assert KronicableTypeChecker(IsoDateTime).is_primitive() is True
        assert KronicableTypeChecker(EmailStr).is_primitive() is True

    def test_is_primitive_optional_and_literal(self):
        assert KronicableTypeChecker(Optional[int]).is_primitive() is True
        assert KronicableTypeChecker(Literal["a", "b"]).is_primitive() is True

    def test_is_primitive_rejects_basemodel(self):
        assert KronicableTypeChecker(Sub).is_primitive() is False

    def test_is_basemodel(self):
        assert KronicableTypeChecker(Sub).is_basemodel() is True
        assert KronicableTypeChecker(int).is_basemodel() is False


class TestValidContainers:
    def test_list_variants(self):
        assert KronicableTypeChecker(list[int]).is_valid_list() is True
        assert KronicableTypeChecker(list[Sub]).is_valid_list() is True
        assert KronicableTypeChecker(list[Literal["O", "I"]]).is_valid_list() is True
        assert KronicableTypeChecker(list[Any]).is_valid_list() is False
        assert KronicableTypeChecker(list).is_valid_list() is False
        assert KronicableTypeChecker(dict[str, int]).is_valid_list() is False

    def test_dict_variants(self):
        assert KronicableTypeChecker(dict[str, int]).is_valid_dict() is True
        assert KronicableTypeChecker(dict[str, Sub]).is_valid_dict() is True
        assert KronicableTypeChecker(dict[str, Literal["O", "I"]]).is_valid_dict() is True
        assert KronicableTypeChecker(dict[str, Any]).is_valid_dict() is False
        assert KronicableTypeChecker(dict).is_valid_dict() is False
        assert KronicableTypeChecker(dict[int, int]).is_valid_dict() is False


class TestIsValid:
    def test_valid_shapes(self):
        assert KronicableTypeChecker(int).is_valid() is True
        assert KronicableTypeChecker(Sub).is_valid() is True
        assert KronicableTypeChecker(list[int]).is_valid() is True
        assert KronicableTypeChecker(dict[str, int]).is_valid() is True

    def test_optional_inner_is_validated(self):
        assert KronicableTypeChecker(Optional[int]).is_valid() is True

    def test_invalid_type_returns_false(self):
        class NotAllowed:
            pass

        assert KronicableTypeChecker(NotAllowed).is_valid() is False

    def test_optional_with_bad_inner_returns_false(self):
        assert KronicableTypeChecker(Optional[Union[int, str]]).is_valid() is False


class TestToKronicleType:
    def test_primitive_types(self):
        assert KronicableTypeChecker(str).to_kronicle_type() == "str"
        assert KronicableTypeChecker(float).to_kronicle_type() == "float"
        assert KronicableTypeChecker(datetime).to_kronicle_type() == "datetime"
        assert KronicableTypeChecker(list).to_kronicle_type() == "list"
        assert KronicableTypeChecker(dict).to_kronicle_type() == "dict"

    def test_bool_maps_to_int_quirk(self):
        # bool is a subclass of int and int is checked first in COL_TO_PY_TYPE
        assert KronicableTypeChecker(bool).to_kronicle_type() == "int"

    def test_optional_unwraps_inner(self):
        assert KronicableTypeChecker(Optional[int]).to_kronicle_type() == "optional[int]"

    def test_string_optional_unwraps_inner(self):
        assert KronicableTypeChecker("optional[int]").to_kronicle_type() == "optional[int]"

    def test_literal_is_unwrapped(self):
        assert KronicableTypeChecker(Literal["O", "I"]).to_kronicle_type() == "str"

    def test_generic_list_and_dict(self):
        assert KronicableTypeChecker(list[int]).to_kronicle_type() == "list"
        assert KronicableTypeChecker(dict[str, int]).to_kronicle_type() == "dict"

    def test_iso_datetime_maps_to_datetime(self):
        assert KronicableTypeChecker(IsoDateTime).to_kronicle_type() == "datetime"

    def test_basemodel_maps_to_dict(self):
        assert KronicableTypeChecker(Sub).to_kronicle_type() == "dict"

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError, match="is not Kronicable"):
            KronicableTypeChecker(Any).to_kronicle_type()

    def test_fallback_branch_is_dead_but_reachable_white_box(self):
        # is_valid() cannot be True for a non-type that avoids every branch above,
        # so we force the fallback to exercise the defensive return.
        kt = KronicableTypeChecker(123)
        kt.is_valid = lambda: True  # type: ignore[method-assign]
        kt.is_optional = lambda: False  # type: ignore[method-assign]
        assert kt.to_kronicle_type() == "str"


class TestDescribeAndMaps:
    def test_describe(self):
        assert KronicableTypeChecker(int).describe() == str(int)

    def test_str_to_py_type_map(self):
        mapping = KronicableTypeChecker.str_to_py_type_map()
        assert mapping == dict(COL_TO_PY_TYPE.items())
        assert mapping["int"] is int

    def test_py_to_str_type_map(self):
        mapping = KronicableTypeChecker.py_to_str_type_map()
        assert mapping[int] == "int"
        assert mapping[str] == "str"

    def test_module_level_constants(self):
        assert "int" in STR_TYPES
        assert "IsoDateTime" in EXT_STR_TYPES
        assert IsoDateTime in PRIMITIVE_TYPES
