# tests/models/test_kronicle_channel.py
from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.data.kronicle_column_metadata import KronicleColumnMetadata
from kronicle_sdk.models.rbac.kronicle_zone import KronicleZone


class _NoStr:
    """Object whose ``__str__`` attribute is not callable."""

    __str__ = None  # type: ignore


class TestAvailableRows:
    def test_populated_from_op_details(self):
        assert KronicleChannel(op_details={"available_rows": 7}).available_rows == 7

    def test_absent_op_details_stays_none(self):
        assert KronicleChannel().available_rows is None

    def test_falsy_value_is_ignored(self):
        assert KronicleChannel(op_details={"available_rows": 0}).available_rows is None

    def test_explicit_value_is_kept(self):
        assert KronicleChannel(available_rows=3).available_rows == 3


class TestValidateSchema:
    def test_none_schema_returns_none(self):
        assert KronicleChannel._validate_schema(None) is None  # type: ignore

    def test_non_dict_schema_raises(self):
        with pytest.raises(TypeError, match="channel_schema must be a dict"):
            KronicleChannel._validate_schema("not-a-dict")  # type: ignore

    def test_valid_schema_normalized(self):
        c = KronicleChannel(channel_schema={"time": "datetime", "value": "float"})
        assert c.channel_schema == {"time": "datetime", "value": "float"}

    def test_invalid_type_string_raises(self):
        with pytest.raises(ValueError, match="Invalid schema types"):
            KronicleChannel(channel_schema={"x": "nope"})

    def test_non_kronicable_object_raises(self):
        # `Any` cannot be supplied through the typed constructor, so drive the
        # validator directly to hit the is_valid()-False branch.
        with pytest.raises(ValueError, match="Invalid schema types"):
            KronicleChannel._validate_schema({"x": Any})  # type: ignore


class TestNormalizeTags:
    def test_none_returns_none(self):
        assert KronicleChannel.normalize_tags(None) is None

    def test_null_values_are_dropped(self):
        assert KronicleChannel.normalize_tags({"a": None}) == {}

    def test_dict_value_raises(self):
        with pytest.raises(TypeError, match="is a dict and is not allowed"):
            KronicleChannel.normalize_tags({"a": {"nested": 1}})

    def test_datetime_is_isoformatted(self):
        value = datetime(2025, 1, 1)
        assert KronicleChannel.normalize_tags({"t": value}) == {"t": value.astimezone().isoformat()}

    def test_primitives_and_lists_kept(self):
        out = KronicleChannel.normalize_tags({"a": 1, "b": "x", "c": [1, 2], "d": True, "e": 1.5})
        assert out == {"a": 1, "b": "x", "c": [1, 2], "d": True, "e": 1.5}

    def test_other_objects_are_stringified(self):
        value = uuid4()
        assert KronicleChannel.normalize_tags({"u": value}) == {"u": str(value)}

    def test_unserializable_object_raises(self):
        with pytest.raises(TypeError, match="cannot be serialized"):
            KronicleChannel.normalize_tags({"k": _NoStr()})

    def test_constructor_applies_normalization(self):
        c = KronicleChannel(tags={"t": datetime(2025, 1, 1), "d": None})  # type: ignore
        assert c.tags is not None
        assert set(c.tags) == {"t"}


class TestColumnMetadata:
    def test_default_is_none(self):
        assert KronicleChannel().column_metadata is None

    def test_explicit_none_is_kept(self):
        assert KronicleChannel(column_metadata=None).column_metadata is None

    def test_non_dict_field_raises(self):
        with pytest.raises(ValidationError):
            KronicleChannel(column_metadata="nope")  # type: ignore[arg-type]

    def test_none_omitted_from_dump(self):
        assert "column_metadata" not in KronicleChannel(name="test.chan").model_dump()

    def test_raw_dict_values_are_coerced(self):
        c = KronicleChannel(column_metadata={"temperature": {"unit": "Cel"}})
        assert c.column_metadata is not None
        entry = c.column_metadata["temperature"]
        assert isinstance(entry, KronicleColumnMetadata)
        assert entry.unit == "Cel"

    def test_model_values_are_kept(self):
        cm = KronicleColumnMetadata(unit="Cel")
        c = KronicleChannel(column_metadata={"temperature": cm})
        assert c.column_metadata is not None
        assert c.column_metadata["temperature"] is cm

    def test_malformed_value_raises(self):
        with pytest.raises(ValidationError):
            KronicleChannel(column_metadata={"temperature": {"unit": 123}})  # type: ignore[dict-item]

    def test_non_dict_value_raises(self):
        with pytest.raises(ValidationError):
            KronicleChannel(column_metadata={"temperature": "not-a-dict"})  # type: ignore[dict-item]

    def test_dump_keeps_values_and_drops_unset_known_keys(self):
        c = KronicleChannel(column_metadata={"temperature": {"unit": "Cel"}})
        assert c.model_dump()["column_metadata"] == {"temperature": {"unit": "Cel"}}

    def test_dump_preserves_extras(self):
        c = KronicleChannel(column_metadata={"temperature": {"unit": "Cel", "precision": 2}})
        assert c.model_dump()["column_metadata"] == {"temperature": {"unit": "Cel", "precision": 2}}

    def test_empty_column_metadata_is_dropped_from_dump(self):
        assert "column_metadata" not in KronicleChannel(column_metadata={}).model_dump()

    def test_from_json_parses_response(self):
        c = KronicleChannel.from_json({"column_metadata": {"temperature": {"unit": "Cel"}}})
        assert c.column_metadata is not None
        assert isinstance(c.column_metadata["temperature"], KronicleColumnMetadata)


class TestConstructors:
    def test_from_json_normalizes_schema(self):
        c = KronicleChannel.from_json({"channel_schema": {"time": "datetime", "value": "float"}})
        assert c.channel_schema == {"time": "datetime", "value": "float"}

    def test_from_json_zone_dict(self):
        zid = uuid4()
        c = KronicleChannel.from_json({"zone": {"id": str(zid), "name": "test.zone"}})
        assert isinstance(c.zone, KronicleZone)
        assert c.zone.id == zid

    def test_from_json_zone_id_fallback(self):
        zid = uuid4()
        c = KronicleChannel.from_json({"zone_id": str(zid)})
        assert c.zone is not None
        assert c.zone.id == zid

    def test_from_json_alt_channel_id(self):
        cid = uuid4()
        assert KronicleChannel.from_json({"channel_id": str(cid)}).id == cid

    def test_from_str_parses_json(self):
        cid = uuid4()
        c = KronicleChannel.from_str('{"id": "%s", "name": "test.chan"}' % cid)
        assert c.id == cid
        assert c.name == "test.chan"


class TestSerialization:
    def test_to_json(self):
        assert KronicleChannel(name="test.chan").to_json()["name"] == "test.chan"

    def test_model_dump_flatten_with_zone(self):
        zid = uuid4()
        c = KronicleChannel(name="test.chan", zone=KronicleZone(id=zid, name="test.zone"))
        d = c.model_dump(flatten=True)
        assert d["zone_id"] == zid.hex
        assert d["zone_name"] == "test.zone"
        assert "zone" not in d

    def test_model_dump_flatten_without_zone(self):
        d = KronicleChannel(name="test.chan").model_dump(flatten=True)
        assert "zone" not in d

    def test_model_dump_not_flattened_keeps_zone(self):
        zid = uuid4()
        c = KronicleChannel(name="test.chan", zone=KronicleZone(id=zid, name="test.zone"))
        assert c.model_dump()["zone"]["id"] == str(zid)

    def test_to_json_str(self):
        assert '"test.chan"' in KronicleChannel(name="test.chan").to_json_str()

    def test_str(self):
        assert '"test.chan"' in str(KronicleChannel(name="test.chan"))


class TestDataHelpers:
    def test_rows_to_columns_without_rows_returns_none(self):
        assert KronicleChannel()._rows_to_columns() is None

    def test_rows_to_columns_builds_and_stores_columns(self):
        c = KronicleChannel(rows=[{"a": 1, "b": 2}, {"a": 3, "b": 4}])
        cols = c._rows_to_columns()
        assert cols == {"a": [1, 3], "b": [2, 4]}
        assert c.columns == {"a": [1, 3], "b": [2, 4]}

    def test_ensure_has_id_returns_existing(self):
        cid = uuid4()
        c = KronicleChannel(id=cid, name="test.chan")
        assert c.ensure_has_id() == cid

    def test_ensure_has_id_raises_when_missing(self):
        c = KronicleChannel(name="test.chan")
        c.id = None
        with pytest.raises(ValueError, match="no id"):
            c.ensure_has_id()

    def test_get_columns_returns_existing(self):
        assert KronicleChannel(columns={"a": [1]}).get_columns() == {"a": [1]}

    def test_get_columns_derives_from_rows(self):
        assert KronicleChannel(rows=[{"a": 1}]).get_columns() == {"a": [1]}
