# tests/models/test_row_filter.py
from uuid import uuid4

import pytest

from kronicle_sdk.connectors.channel.channel_reader import KronicleReader
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.data.row_filter import MAX_LIMIT, MAX_OFFSET, RowFilter


class TestRowFilterParams:
    def test_empty_filter_yields_no_params(self):
        assert RowFilter().to_params() == {}

    def test_pagination(self):
        p = RowFilter(limit=50, offset=10).to_params()
        assert p == {"limit": 50, "offset": 10}

    def test_sort_string(self):
        p = RowFilter(sort="target,-time").to_params()
        assert p == {"sort": "target,-time"}

    def test_sort_list(self):
        p = RowFilter(sort=["target", "-time"]).to_params()
        assert p == {"sort": "target,-time"}

    def test_columns_string(self):
        p = RowFilter(columns="time,value").to_params()
        assert p == {"columns": "time,value"}

    def test_columns_list(self):
        p = RowFilter(columns=["time", "value"]).to_params()
        assert p == {"columns": "time,value"}

    def test_single_value_filters_bracket_keys(self):
        p = RowFilter(
            col={"name": "Tintin"},
            min={"time": "2026-03-20"},
            max={"time": "2026-03-21"},
        ).to_params()
        assert p == {
            "col[name]": "Tintin",
            "min[time]": "2026-03-20",
            "max[time]": "2026-03-21",
        }

    def test_multi_value_filters_join(self):
        p = RowFilter(any={"tag": ["room1", "room2"]}, has={"status": ["ok", "fail"]}).to_params()
        assert p == {
            "any[tag]": "room1,room2",
            "has[status]": "ok,fail",
        }

    def test_booleans_lowercased(self):
        p = RowFilter(skip_received=False, strict=True).to_params()
        assert p == {"skip_received": "false", "strict": "true"}

    def test_composite(self):
        p = RowFilter(
            limit=25,
            offset=5,
            sort=["-time"],
            col={"name": "Tintin"},
            any={"tag": ["room1"]},
        ).to_params()
        assert p["limit"] == 25
        assert p["sort"] == "-time"
        assert p["col[name]"] == "Tintin"
        assert p["any[tag]"] == "room1"


class TestRowFilterValidation:
    def test_limit_capped_to_max(self):
        assert RowFilter(limit=10_000).limit == MAX_LIMIT

    def test_offset_capped_to_max(self):
        assert RowFilter(offset=100_000).offset == MAX_OFFSET

    def test_limit_zero_rejected(self):
        with pytest.raises(ValueError):
            RowFilter(limit=0)

    def test_sort_name_normalized(self):
        assert RowFilter(sort=["Time-Value"]).sort == ["time_value"]

    def test_sort_descends_preserved(self):
        assert RowFilter(sort=["-Time"]).sort == ["-time"]

    def test_sort_invalid_raises(self):
        with pytest.raises(ValueError):
            RowFilter(sort=["   "])

    def test_columns_normalized(self):
        assert RowFilter(columns="Time , VALUE").columns == ["time", "value"]

    def test_col_dots_kept(self):
        assert RowFilter(col={"Name.First": "Alice"}).col == {"name.first": "Alice"}

    def test_min_max_normalized_no_dots(self):
        assert RowFilter(min={"Time": "x"}, max={"Value": "y"}).min == {"time": "x"}
        assert RowFilter(max={"Value": "y"}).max == {"value": "y"}

    def test_any_flattens_comma_values(self):
        f = RowFilter(any={"tag": ["room1,room2", "room3"]})
        assert f.any == {"tag": ["room1", "room2", "room3"]}
        assert f.to_params() == {"any[tag]": "room1,room2,room3"}

    def test_invalid_column_name_raises(self):
        with pytest.raises(ValueError):
            RowFilter(col={"!!": "x"})


class TestGetRowsFilters:
    def _reader(self, monkeypatch):
        reader = KronicleReader(url="http://localhost:8765", usr="admin", pwd="secret")
        captured = {}

        def mock_get(*, route, params=None, **kw):
            captured["route"] = route
            captured["params"] = params
            return {"rows": [{"time": "2026-01-01", "value": 1.0}]}

        monkeypatch.setattr(reader, "get", mock_get)
        return reader, captured

    def test_get_rows_without_filter_passes_no_params(self, monkeypatch):
        reader, captured = self._reader(monkeypatch)
        reader.get_rows_for_channel(id=uuid4())
        assert captured["params"] is None

    def test_get_rows_with_filter_passes_params(self, monkeypatch):
        reader, captured = self._reader(monkeypatch)
        cid = uuid4()
        reader.get_rows_for_channel(
            id=cid,
            filter=RowFilter(col={"name": "Tintin"}, limit=10),
        )
        assert str(cid) in captured["route"]
        assert captured["params"] == {"col[name]": "Tintin", "limit": 10}

    def test_get_cols_with_filter_passes_params(self, monkeypatch):
        reader = KronicleReader(url="http://localhost:8765", usr="admin", pwd="secret")
        captured = {}

        def mock_get(*, route, params=None, **kw):
            captured["route"] = route
            captured["params"] = params
            return KronicleChannel(
                id=str(uuid4()),  # type: ignore
                columns={"time": ["2026-01-01"], "value": [1.0]},
            )

        monkeypatch.setattr(reader, "get", mock_get)
        cid = uuid4()
        reader.get_cols_for_channel(
            id=cid,
            filter=RowFilter(columns="time,value"),
        )
        assert "columns" in captured["route"]
        assert captured["params"] == {"columns": "time,value"}
