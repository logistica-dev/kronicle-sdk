# tests/models/test_kronicable_sample.py
from json import dumps
from typing import Any

import pytest
from pydantic import BaseModel, Field, computed_field

from kronicle_sdk.models.data.kronicable_sample import KronicableSample
from kronicle_sdk.models.iso_datetime import IsoDateTime, now_local


class Inner(BaseModel):
    v: int = 0


class Sample(KronicableSample):
    time: IsoDateTime
    name: str = "n"
    score: float = 0.0
    note: str | None = None
    inner: Inner | None = None
    inners: list[Inner] | None = None
    mapping: dict[str, Inner] | None = None

    @computed_field
    @property
    def double(self) -> int:
        return len(self.name) * 2


class RowSample(KronicableSample):
    req: int
    opt: int | None = None
    inner: Inner | None = None
    inners: list[Inner] | None = None
    mapping: dict[str, Inner] | None = None
    label: str = "x"

    @computed_field
    @property
    def double(self) -> int:
        return self.req * 2


class TestFieldValidation:
    def test_invalid_field_type_raises(self):
        class Bad(KronicableSample):
            value: Any

        with pytest.raises(TypeError, match="unsupported type for Kronicable"):
            Bad(value=1)

    def test_valid_field_types_accepted(self):
        assert Sample(time=now_local()).name == "n"


class TestListFields:
    def test_list_fields_merges_regular_and_computed(self):
        fields = Sample.list_fields()
        assert "time" in fields
        assert "double" in fields


class TestChannelSchema:
    def test_channel_schema_covers_regular_and_computed(self):
        sample = Sample(time=now_local(), name="hello")
        schema = sample.channel_schema
        assert schema["time"] == "datetime"
        assert schema["name"] == "str"
        assert schema["score"] == "float"
        assert schema["note"] == "optional[str]"
        assert schema["inner"] == "optional[dict]"
        assert schema["inners"] == "optional[list]"
        assert schema["mapping"] == "optional[dict]"
        assert schema["double"] == "int"


class TestFieldDescriptions:
    def test_only_described_fields_are_returned(self):
        class Described(KronicableSample):
            a: int = Field(default=1, description="the a")
            b: int = 2

        assert Described.get_field_descriptions() == {"a": "the a"}

    def test_no_descriptions_returns_empty_dict(self):
        assert Sample.get_field_descriptions() == {}


class TestToRow:
    def test_optional_none_skipped_and_primitives_passed_through(self):
        row = RowSample(req=3, label="hi").to_row()
        assert row == {"req": 3, "label": "hi", "double": 6}

    def test_required_none_raises(self):
        sample = RowSample(req=1)
        sample.req = None  # type: ignore  # bypass assignment validation deliberately # type: ignore
        with pytest.raises(ValueError, match="required but has value None"):
            sample.to_row()

    def test_nested_basemodel_dumped(self):
        row = RowSample(req=1, inner=Inner(v=2)).to_row()
        assert row["inner"] == {"v": 2}

    def test_list_of_basemodels_json_dumped(self):
        row = RowSample(req=1, inners=[Inner(v=2), Inner(v=3)]).to_row()
        assert row["inners"] == dumps([{"v": 2}, {"v": 3}])

    def test_dict_of_basemodels_json_dumped(self):
        row = RowSample(req=1, mapping={"a": Inner(v=1)}).to_row()
        assert row["mapping"] == dumps({"a": {"v": 1}})

    def test_empty_containers_passed_through(self):
        row = RowSample(req=1, inners=[], mapping={}).to_row()
        assert row["inners"] == []
        assert row["mapping"] == {}
