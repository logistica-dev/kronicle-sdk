# tests/models/test_kronicle_column_metadata.py
import pytest

from kronicle_sdk.models.data.kronicle_column_metadata import KronicleColumnMetadata


class TestToJson:
    def test_all_none_is_empty(self):
        assert KronicleColumnMetadata().to_json() == {}

    def test_known_fields(self):
        cm = KronicleColumnMetadata(
            unit="Cel",
            description="Air temperature",
            ontology="http://purl.obolibrary.org/obo/NCIT_C1910",
        )
        assert cm.to_json() == {
            "unit": "Cel",
            "description": "Air temperature",
            "ontology": "http://purl.obolibrary.org/obo/NCIT_C1910",
        }

    def test_unset_known_keys_are_dropped(self):
        assert KronicleColumnMetadata(unit="Cel").to_json() == {"unit": "Cel"}

    def test_extras_are_kept(self):
        cm = KronicleColumnMetadata(unit="%", precision=2)  # type: ignore[reportCallIssue]
        assert cm.to_json() == {"unit": "%", "precision": 2}


class TestConstraints:
    def test_unknown_descriptors_are_allowed(self):
        cm = KronicleColumnMetadata(source="sensor-A")  # type: ignore[reportCallIssue]
        assert cm.to_json() == {"source": "sensor-A"}

    def test_unit_too_long_raises(self):
        with pytest.raises(ValueError):
            KronicleColumnMetadata(unit="x" * 65)

    def test_description_too_long_raises(self):
        with pytest.raises(ValueError):
            KronicleColumnMetadata(description="x" * 4097)

    def test_ontology_too_long_raises(self):
        with pytest.raises(ValueError):
            KronicleColumnMetadata(ontology="x" * 513)

    def test_ontology_is_not_uri_validated(self):
        # Server intentionally does not URI-validate `ontology`.
        assert KronicleColumnMetadata(ontology="not a uri").ontology == "not a uri"
