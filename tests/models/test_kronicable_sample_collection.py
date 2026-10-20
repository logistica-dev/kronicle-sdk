# tests/models/test_kronicable_sample_collection.py
from uuid import uuid4

import pytest

from kronicle_sdk.models.data.kronicable_sample import KronicableSample
from kronicle_sdk.models.data.kronicable_sample_collection import KronicableSampleCollection
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.iso_datetime import IsoDateTime, now_local


class Metric(KronicableSample):
    time: IsoDateTime
    value: float = 0.0
    note: str | None = None


class OtherMetric(KronicableSample):
    time: IsoDateTime
    count: int = 0


def _base() -> KronicleChannel:
    return KronicleChannel(id=uuid4(), name="transfer_channel")


def _metric(value: float = 1.0, note: str | None = None) -> Metric:
    return Metric(time=now_local(), value=value, note=note)


class TestInit:
    def test_defaults(self):
        base = _base()
        collection = KronicableSampleCollection(base)
        assert collection.base_payload is base
        assert collection.samples == []
        assert collection._schema is None

    def test_initial_samples_are_copied(self):
        sample = _metric()
        collection = KronicableSampleCollection(_base(), [sample])
        assert collection.samples == [sample]


class TestAddSample:
    def test_first_sample_sets_schema(self):
        collection = KronicableSampleCollection(_base())
        sample = _metric()
        collection.add_sample(sample)
        assert collection._schema == sample.channel_schema
        assert collection.samples == [sample]

    def test_matching_schema_appends(self):
        collection = KronicableSampleCollection(_base())
        collection.add_sample(_metric(1.0))
        collection.add_sample(_metric(2.0))
        assert len(collection.samples) == 2

    def test_schema_mismatch_raises(self):
        collection = KronicableSampleCollection(_base())
        collection.add_sample(_metric())
        with pytest.raises(ValueError, match="schema mismatch"):
            collection.add_sample(OtherMetric(time=now_local()))

    def test_add_sample_list(self):
        collection = KronicableSampleCollection(_base())
        collection.add_sample_list([_metric(1.0), _metric(2.0)])
        assert len(collection.samples) == 2


class TestRows:
    def test_empty_collection_returns_empty_list(self):
        collection = KronicableSampleCollection(_base())
        assert collection.rows == []

    def test_missing_schema_raises(self):
        # samples provided directly, so _schema is never populated
        collection = KronicableSampleCollection(_base(), [_metric()])
        with pytest.raises(ValueError, match="No schema was provided"):
            _ = collection.rows

    def test_rows_are_built_from_schema(self):
        collection = KronicableSampleCollection(_base())
        sample = _metric(3.5, note="ok")
        collection.add_sample(sample)
        rows = collection.rows
        assert rows == [{name: getattr(sample, name, None) for name in sample.channel_schema}]


class TestToKronicleChannel:
    def test_empty_collection_raises(self):
        with pytest.raises(ValueError, match="No sample to convert"):
            KronicableSampleCollection(_base()).to_kronicle_channel()

    def test_missing_schema_raises(self):
        collection = KronicableSampleCollection(_base(), [_metric()])
        with pytest.raises(ValueError, match="No schema was provided"):
            collection.to_kronicle_channel()

    def test_payload_carries_rows_and_schema(self):
        collection = KronicableSampleCollection(_base())
        sample = _metric(7.5)
        collection.add_sample(sample)
        payload = collection.to_kronicle_channel()
        assert payload.rows == collection.rows
        assert payload.channel_schema == collection._schema
        assert payload.name == "transfer_channel"
