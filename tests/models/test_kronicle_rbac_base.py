# tests/models/test_kronicle_rbac_base.py
from uuid import uuid4

import pytest

from kronicle_sdk.models.rbac.kronicle_group import KronicleGroup
from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase


class TestKronicleRbacBaseValidation:
    def test_explicit_none_id_stays_none(self):
        # An omitted/None id means "not persisted yet" and must not be fabricated.
        g = KronicleGroup(id=None, name="test.group")
        assert g.id is None

    def test_valid_uuid_string_is_normalized(self):
        uid = uuid4()
        assert KronicleGroup(id=str(uid)).id == uid  # type: ignore

    def test_ensure_has_id_raises_when_absent(self):
        with pytest.raises(ValueError, match="no id"):
            KronicleGroup(name="test.group").ensure_has_id()

    def test_ensure_has_id_returns_id(self):
        uid = uuid4()
        assert KronicleGroup(id=uid, name="test.group").ensure_has_id() == uid

    def test_explicit_none_name_is_kept(self):
        assert KronicleGroup(name=None).name is None

    def test_default_name_is_none(self):
        assert KronicleGroup().name is None

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError):
            KronicleGroup(name="ab")

    def test_explicit_none_details_is_kept(self):
        assert KronicleGroup(details=None).details is None

    def test_small_details_ok(self):
        assert KronicleGroup(details={"a": 1}).details == {"a": 1}

    def test_details_too_large_raises(self):
        with pytest.raises(ValueError, match="too large"):
            KronicleGroup(details={"big": "x" * (70 * 1024)})


class TestKronicleRbacBaseSerialization:
    def test_to_json(self):
        assert KronicleGroup(name="test.group").to_json()["name"] == "test.group"

    def test_model_dump_json(self):
        assert "test.group" in KronicleGroup(name="test.group").model_dump_json()

    def test_from_json(self):
        g = KronicleGroup.from_json({"name": "test.group"})
        assert isinstance(g, KronicleGroup)
        assert g.name == "test.group"

    def test_str_strips_kronicle_prefix(self):
        assert str(KronicleGroup(name="test.group")).startswith("KGroup ")


class TestExtractField:
    def test_missing_field_raises(self):
        with pytest.raises(ValueError, match="not found"):
            KronicleRbacBase._extract_field({}, "role", KronicleGroup)

    def test_falsy_field_raises(self):
        with pytest.raises(ValueError, match="not found"):
            KronicleRbacBase._extract_field({"role": None}, "role", KronicleGroup)

    def test_uses_from_json_when_available(self):
        out = KronicleRbacBase._extract_field({"role": {"name": "test.group"}}, "role", KronicleGroup)
        assert isinstance(out, KronicleGroup)
        assert out.name == "test.group"

    def test_plain_type_success(self):
        assert KronicleRbacBase._extract_field({"n": 5}, "n", int) == 5

    def test_plain_type_failure_wraps_error(self):
        with pytest.raises(ValueError, match="is not a int"):
            KronicleRbacBase._extract_field({"n": "not-an-int"}, "n", int)
