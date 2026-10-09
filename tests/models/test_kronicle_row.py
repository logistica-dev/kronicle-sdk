# tests/models/test_kronicle_row.py
from uuid import uuid4

import pytest

from kronicle_sdk.models.rbac.kronicle_row import KronicleRow


class TestKronicleRow:
    def test_valid_row(self):
        cid = uuid4()
        row = KronicleRow(id=5, channel_id=cid, name="test.row")
        assert row.id == 5
        assert row.channel_id == cid

    def test_non_integer_id_raises(self):
        with pytest.raises(ValueError, match="row id must be an integer"):
            KronicleRow(id="abc", channel_id=uuid4())  # type: ignore

    def test_float_id_raises(self):
        with pytest.raises(ValueError, match="row id must be an integer"):
            KronicleRow(id=1.5, channel_id=uuid4())  # type: ignore
