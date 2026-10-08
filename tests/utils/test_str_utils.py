# tests/utils/test_str_utils.py
import re
from base64 import urlsafe_b64encode
from datetime import datetime, timezone
from uuid import UUID, uuid1, uuid4

import pytest
from pydantic import BaseModel

from kronicle_sdk.utils.str_utils import (
    REGEX_UUID,
    SQL_COL_MAX_LEN,
    check_is_str,
    check_is_uuid4,
    decode_b64url,
    encode_b64url,
    enforce_length,
    ensure_uuid4,
    get_type,
    is_base64_url,
    is_uuid_v4,
    normalize_column_name,
    normalize_name,
    normalize_name_keep_dots,
    normalize_sort_name,
    normalize_to_snake_case,
    now_iso_str,
    pad_b64_str,
    param_dict_to_str,
    serialize,
    slash_join,
    split_strip,
    strip_quotes,
    tiny_id,
    uuid4_str,
    uuid_to_str,
    validate_orcid,
)


class TestEnforceLength:
    def test_pads_shorter_string(self):
        assert enforce_length("here", 15) == "here".ljust(15)

    def test_default_length(self):
        assert len(enforce_length("ab")) == 12

    def test_exact_length_unchanged(self):
        assert enforce_length("12345", 5) == "12345"

    def test_truncates_longer_string(self):
        assert enforce_length("a-very-long-here-value", 15) == "a-very-long-her"


class TestSlashJoin:
    def test_joins_fragments(self):
        assert slash_join("api", "v1", "items") == "api/v1/items"

    def test_strips_edge_slashes(self):
        assert slash_join("/api/", "/v1/") == "api/v1"

    def test_skips_none_and_empty(self):
        assert slash_join("a", None, "", "b") == "a/b"

    def test_keeps_inner_scheme_slashes(self):
        assert slash_join("https://example.com/", "/path") == "https://example.com/path"

    def test_no_args_returns_empty(self):
        assert slash_join() == ""

    def test_non_string_raises(self):
        with pytest.raises(AttributeError, match="input parameters must be strings"):
            slash_join("a", 42)


class TestCheckIsStr:
    def test_returns_string(self):
        assert check_is_str("ok") == "ok"

    def test_non_string_raises(self):
        with pytest.raises(TypeError, match="A string is expected"):
            check_is_str(42)


class TestGetType:
    def test_builtin_type_names(self):
        assert get_type("x") == "str"
        assert get_type([]) == "list"

    def test_custom_class_name(self):
        class Foo:
            pass

        assert get_type(Foo()) == "Foo"


class TestUuidHelpers:
    def test_uuid4_str_is_valid_uuid4(self):
        value = uuid4_str()
        assert is_uuid_v4(value)
        assert REGEX_UUID.match(value)

    def test_regexp_rejects_uuid1(self):
        assert REGEX_UUID.match(str(uuid4()))
        assert not REGEX_UUID.match(str(uuid1()))

    @pytest.mark.parametrize("value", [42, None])
    def test_scalar_passthrough(self, value):
        assert uuid_to_str(value) == value

    def test_uuid_becomes_hex(self):
        u = uuid4()
        assert uuid_to_str(u) == u.hex

    def test_uuid_to_str_recurses_into_dicts(self):
        u = uuid4()
        assert uuid_to_str({"id": u, "nested": {"id": u}, "n": 1}) == {
            "id": u.hex,
            "nested": {"id": u.hex},
            "n": 1,
        }

    def test_uuid_to_str_leaves_lists_untouched(self):
        u = uuid4()
        assert uuid_to_str([u]) == [u]


class TestIsUuidV4:
    def test_valid_string_and_uuid(self):
        assert is_uuid_v4(str(uuid4()))
        assert is_uuid_v4(uuid4())

    def test_other_version_returns_false(self):
        assert not is_uuid_v4(str(uuid1()))
        assert not is_uuid_v4(uuid1())

    @pytest.mark.parametrize("value", [None, 42, "not-a-uuid", ""])
    def test_invalid_input_returns_false(self, value):
        assert not is_uuid_v4(value)


class TestCheckIsUuid4:
    def test_accepts_string(self):
        u = uuid4()
        assert check_is_uuid4(str(u)) == str(u)

    def test_accepts_uuid_object(self):
        assert check_is_uuid4(uuid4()) is not None

    def test_normalizes_uppercase(self):
        upper = str(uuid4()).upper()
        assert check_is_uuid4(upper) == upper.lower()

    @pytest.mark.parametrize("value", [None, 123, "not-a-uuid", str(uuid1())])
    def test_rejects_invalid_values(self, value):
        with pytest.raises(ValueError, match="not a valid UUID v4|should not be null"):
            check_is_uuid4(value)


class TestEnsureUuid4:
    def test_returns_uuid_object(self):
        uid = ensure_uuid4(str(uuid4()))
        assert isinstance(uid, UUID)
        assert uid.version == 4

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Invalid UUID format"):
            ensure_uuid4("not-a-uuid")

    def test_wrong_version_raises(self):
        with pytest.raises(ValueError, match="must be a UUIDv4"):
            ensure_uuid4(uuid1())


class TestStripQuotes:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ('"abc"', "abc"),
            ("'abc'", "abc"),
            ('"a', '"a'),
            ("'\"", "'\""),
            ('"', '"'),
            ("abc", "abc"),
            (42, 42),
            (None, None),
        ],
    )
    def test_strip_matching_quotes_only(self, value, expected):
        assert strip_quotes(value) == expected


class TestSplitStrip:
    def test_splits_and_strips(self):
        assert split_strip("a, b , c") == ["a", "b", "c"]

    def test_drops_empty_parts(self):
        assert split_strip("a,,b, ") == ["a", "b"]

    def test_none_returns_empty_list(self):
        assert split_strip(None) == []

    def test_default_argument_returns_empty_list(self):
        assert split_strip() == []

    def test_custom_separator(self):
        assert split_strip("a|b", sep="|") == ["a", "b"]

    def test_normalization_filter(self):
        assert split_strip("1, 2", norm=int) == [1, 2]

    def test_norm_dropping_none_parts(self):
        assert split_strip("a,,b", norm=lambda p: p or None) == ["a", "b"]


class TestNormalizeName:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("My Col Name", "my_col_name"),
            ("  a  b  ", "a_b"),
            ("a__b", "a_b"),
            ("_x_", "x"),
            ("already_snake", "already_snake"),
            ("UPPER", "upper"),
        ],
    )
    def test_basic_normalization(self, raw, expected):
        assert normalize_name(raw) == expected

    def test_truncates_to_sql_col_max_len(self):
        assert len(normalize_name("a" * 100)) == SQL_COL_MAX_LEN

    def test_leading_digit_needs_prefix(self):
        assert normalize_name("2024_col", prefix="col_") == "col_2024_col"
        with pytest.raises(ValueError):
            normalize_name("2024_col")

    @pytest.mark.parametrize("bad", ["", "___", "!!!"])
    def test_invalid_names_raise(self, bad):
        with pytest.raises(ValueError):
            normalize_name(bad)

    @pytest.mark.parametrize("bad", [None, 123, ["a"]])
    def test_non_string_raises_type_error(self, bad):
        with pytest.raises(TypeError, match="Name should be a string"):
            normalize_name(bad)

    def test_keep_dots(self):
        assert normalize_name("a.b-c", keep_dots=True) == "a.b_c"
        assert normalize_name("a.b-c") == "a_b_c"

    def test_keep_dots_invalid_inner_part_raises(self):
        with pytest.raises(ValueError, match="Name is invalid"):
            normalize_name("a..b", keep_dots=True)

    def test_normalize_name_keep_dots_helper(self):
        assert normalize_name_keep_dots("dim.value") == "dim.value"
        assert normalize_name_keep_dots("My.Col") == "my.col"

    def test_prefix_not_propagated_into_dotted_parts(self):
        # Known quirk: with keep_dots, each segment is normalized without the
        # prefix, so a digit-leading segment raises before the prefix can apply.
        with pytest.raises(ValueError, match="Name is invalid"):
            normalize_name_keep_dots("9x", prefix="p_")


class TestNormalizeSortName:
    def test_plain_field(self):
        assert normalize_sort_name(" Name ") == "name"

    def test_descending_prefix_preserved(self):
        assert normalize_sort_name("-Time") == "-time"

    @pytest.mark.parametrize("bad", ["", "-", "  "])
    def test_empty_or_lone_dash_raises(self, bad):
        with pytest.raises(ValueError):
            normalize_sort_name(bad)


class TestNormalizeToSnakeCase:
    def test_lowercases_and_replaces_separators(self):
        assert normalize_to_snake_case("A-B C") == "a_b_c"

    def test_keeps_word_chars(self):
        assert normalize_to_snake_case("Col_1") == "col_1"


class TestNormalizeColumnName:
    def test_basic(self):
        assert normalize_column_name("My Col") == "my_col"

    def test_leading_digit_gets_prefix(self):
        assert normalize_column_name("9lives") == "col_9lives"

    def test_strips_edge_underscores(self):
        assert normalize_column_name("_x_") == "x"

    def test_empty_string_gets_random_name(self):
        assert re.fullmatch(r"col_[a-z0-9]{8}", normalize_column_name(""))

    @pytest.mark.parametrize("raw", ["_", "!!!", " "])
    def test_input_normalizing_to_empty_raises_index_error(self, raw):
        # Known gap: only the empty *input* is special-cased. Input that is
        # non-empty but normalizes to "" still hits `s[0]` on line 207.
        with pytest.raises(IndexError):
            normalize_column_name(raw)


class TestNowIsoStr:
    def test_default_timespec(self):
        parsed = datetime.fromisoformat(now_iso_str())
        assert parsed.tzinfo is not None

    def test_milliseconds_timespec(self):
        assert "." in now_iso_str(timespec="milliseconds")


class TestBase64:
    def test_pad_b64_str(self):
        assert pad_b64_str("abc") == "abc="
        assert pad_b64_str("a") == "a==="
        assert pad_b64_str("abcd") == "abcd"

    @pytest.mark.parametrize("value", ["aGVsbG8=", "", "____"])
    def test_is_base64_url_valid(self, value):
        assert is_base64_url(value)

    def test_is_base64_url_accepts_bytes(self):
        assert is_base64_url(b"aGVsbG8=")
        assert not is_base64_url(b"not base64!!")

    @pytest.mark.parametrize("value", ["not base64!!", "aGVsbG8", 42, "é"])
    def test_is_base64_url_invalid(self, value):
        assert not is_base64_url(value)

    def test_encode_decode_roundtrip(self):
        assert decode_b64url(encode_b64url("hello world")) == "hello world"

    def test_decode_handles_unpadded_input(self):
        assert decode_b64url("aGVsbG8") == "hello"

    def test_decode_unicode_roundtrip(self):
        assert decode_b64url(encode_b64url("héllo ☃")) == "héllo ☃"

    def test_decode_rejects_non_base64(self):
        with pytest.raises(ValueError, match="should be encoded in base64url"):
            decode_b64url("not valid!!")

    def test_decode_rejects_non_utf8_payload(self):
        payload = urlsafe_b64encode(bytes([0xFF, 0xFE])).decode()
        with pytest.raises(ValueError, match="not properly encoded"):
            decode_b64url(payload)


class TestParamDictToStr:
    def test_none_and_empty(self):
        assert param_dict_to_str(None) == ""
        assert param_dict_to_str({}) == ""

    def test_builds_query_string(self):
        assert param_dict_to_str({"a": 1, "b": "x"}) == "?a=1&b=x"


class TestSerialize:
    @pytest.mark.parametrize("value", [42, 0, False, True, 2.5])
    def test_numbers_and_bools_pass_through(self, value):
        assert serialize(value) is value

    def test_empty_containers_and_str_become_none(self):
        assert serialize("") is None
        assert serialize([]) is None
        assert serialize({}) is None
        assert serialize(set()) is None

    def test_exclude_none_false_keeps_empty_values(self):
        assert serialize("", exclude_none=False) == ""
        assert serialize([], exclude_none=False) == []

    def test_list_drops_nones_and_empty_strings(self):
        assert serialize([0, "", None, "x"]) == [0, "x"]

    def test_list_keeps_nones_when_not_excluding(self):
        assert serialize([1, None], exclude_none=False) == [1, None]

    def test_tuple_stays_tuple(self):
        assert serialize((1, None)) == (1,)
        assert isinstance(serialize((1, 2)), tuple)

    def test_set_becomes_list(self):
        assert serialize({1, 2}) == sorted(serialize({1, 2}))
        assert isinstance(serialize({1, 2}), list)

    def test_uuid_becomes_hex(self):
        u = uuid4()
        assert serialize(u) == u.hex
        assert serialize({"id": u}) == {"id": u.hex}

    def test_nested_structures(self):
        # empty dicts are kept (only None values are dropped)
        assert serialize({"x": [1, None], "y": {"z": None}}) == {"x": [1], "y": {}}

    def test_model_dump(self):
        class Sample(BaseModel):
            a: int = 1
            b: str | None = None

        assert serialize(Sample(a=2)) == {"a": 2}
        assert serialize(Sample(a=2), exclude_none=False) == {"a": 2, "b": None}

    def test_other_objects_returned_as_is(self):
        obj = datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert serialize(obj) is obj


class TestValidateOrcid:
    @pytest.mark.parametrize(
        "raw",
        [
            "0000-0002-1825-0097",
            " 0000-0002-1825-0097 ",
            "https://orcid.org/0000-0002-1825-0097",
            "http://orcid.org/0000-0002-1825-0097",
            "orcid.org/0000-0002-1825-0097",
        ],
    )
    def test_valid_orcid_returns_bare_id(self, raw):
        assert validate_orcid(raw) == "0000-0002-1825-0097"

    @pytest.mark.parametrize("bad", ["not-an-orcid", "0000-0002-1825", "0000000218250097"])
    def test_invalid_orcid_raises(self, bad):
        with pytest.raises(ValueError, match="not a valid ORCID"):
            validate_orcid(bad)


class TestTinyId:
    @pytest.mark.parametrize("n", [1, 8, 16, 32])
    def test_length(self, n):
        value = tiny_id(n)
        assert len(value) == n
        assert re.fullmatch(r"[0-9a-f]+", value)

    @pytest.mark.parametrize("n", [0, -3])
    def test_invalid_length_defaults_to_eight(self, n):
        assert len(tiny_id(n)) == 8

    def test_ids_are_unique(self):
        assert len({tiny_id() for _ in range(100)}) == 100
