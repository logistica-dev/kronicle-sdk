# tests/utils/test_dict_utils.py
import pytest

from kronicle_sdk.utils.dict_utils import (
    ensure_dict_or_none,
    remove_alt_field,
    rows_to_columns,
    skip_nones,
    strip_nulls,
)


class TestEnsureDictOrNone:
    def test_none_returns_empty_dict(self):
        assert ensure_dict_or_none(None) == {}

    def test_valid_dict_returned_as_is(self):
        d = {"a": 1}
        assert ensure_dict_or_none(d) is d

    def test_non_dict_raises_type_error(self):
        with pytest.raises(TypeError, match="Must be a dict or None"):
            ensure_dict_or_none(["not", "a", "dict"])

    def test_non_dict_with_field_name_raises(self):
        with pytest.raises(TypeError, match="payload must be a dict or None"):
            ensure_dict_or_none([], field_name="payload")

    @pytest.mark.parametrize("bad_key", ["", "   "])
    def test_blank_key_raises_value_error(self, bad_key):
        with pytest.raises(ValueError, match="Key cannot be empty"):
            ensure_dict_or_none({bad_key: 1})

    def test_blank_key_with_field_name_raises(self):
        with pytest.raises(ValueError, match="Key cannot be empty for payload"):
            ensure_dict_or_none({"": 1}, field_name="payload")


class TestRowsToColumns:
    def test_basic_conversion(self):
        rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        assert rows_to_columns(rows) == {"a": [1, 3], "b": [2, 4]}

    def test_empty_rows(self):
        assert rows_to_columns([]) == {}

    def test_ragged_rows(self):
        rows = [{"a": 1}, {"b": 2}, {"a": 3, "b": 4}]
        assert rows_to_columns(rows) == {"a": [1, 3], "b": [2, 4]}


class TestStripNulls:
    def test_dict_shallow(self):
        assert strip_nulls({"a": 1, "b": None, "c": 0, "d": False, "e": ""}) == {"a": 1, "c": 0, "d": False, "e": ""}

    def test_dict_recursive(self):
        obj = {"a": None, "e": {"g": None, "h": "x"}, "l": [1, None]}
        assert strip_nulls(obj, recursive=True) == {"e": {"h": "x"}, "l": [1]}

    def test_dict_shallow_keeps_nested_nulls(self):
        obj = {"e": {"g": None}}
        assert strip_nulls(obj, recursive=False) == {"e": {"g": None}}

    def test_list(self):
        assert strip_nulls([3, 0, 5, None]) == [3, 0, 5]

    def test_list_recursive_strips_inner_dicts(self):
        assert strip_nulls([{"a": None, "b": 1}, None, 2], recursive=True) == [{"b": 1}, 2]

    @pytest.mark.parametrize("scalar", ["tutu", 0, False])
    def test_non_containers_unchanged(self, scalar):
        assert strip_nulls(scalar) == scalar


class TestSkipNones:
    def test_drops_none_values_only(self):
        assert skip_nones({"a": True, "b": False, "c": None, "d": {}}) == {"a": True, "b": False, "d": {}}

    def test_empty_dict(self):
        assert skip_nones({}) == {}


class TestRemoveAltField:
    def test_renames_alt_to_keep(self):
        d = {"alt": 2}
        remove_alt_field(d, keep="keep", alt="alt")
        assert d == {"keep": 2}

    def test_keep_priority_when_both_present(self):
        d = {"keep": 1, "alt": 2}
        remove_alt_field(d, keep="keep", alt="alt")
        assert d == {"keep": 1}

    def test_noop_when_alt_missing(self):
        d = {"keep": 1}
        remove_alt_field(d, keep="keep", alt="alt")
        assert d == {"keep": 1}
