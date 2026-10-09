# tests/models/test_kronicle_user.py
import pytest

from kronicle_sdk.models.rbac import kronicle_user as user_module
from kronicle_sdk.models.rbac.kronicle_user import KronicleUser, _validate_password


class TestKronicleUserEmailValidation:
    def test_valid_email(self):
        u = KronicleUser(name="test.user", email="user@example.com")
        assert u.email == "user@example.com"

    def test_email_lowercased(self):
        u = KronicleUser(name="test.user", email="User@Example.COM")
        assert u.email == "user@example.com"

    @pytest.mark.parametrize(
        "email",
        [
            "not-an-email",
            "a@",
            "@b.com",
            "a b@c.com",
            "a@b",
        ],
    )
    def test_invalid_email(self, email):
        with pytest.raises(ValueError):
            KronicleUser(name="test.user", email=email)


class TestKronicleUserPasswordValidation:
    def test_no_password_ok(self):
        u = KronicleUser(name="test.user", email="user@example.com")
        assert u.password is None

    def test_valid_password(self):
        u = KronicleUser(name="test.user", email="user@example.com", password="Str0ng!Passw0rd")
        assert u.password == "Str0ng!Passw0rd"

    @pytest.mark.parametrize(
        "password",
        [
            "short1!",
            "alllowercase1!",
            "ALLUPPERCASE1!",
            "NoDigitsHere!",
            "NoSpecialChars1",
        ],
    )
    def test_invalid_password(self, password):
        with pytest.raises(ValueError):
            KronicleUser(name="test.user", email="user@example.com", password=password)


class TestValidatePasswordHelper:
    def test_none_returns_none(self):
        assert _validate_password(None) is None

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_password("")

    def test_too_long_rejected(self):
        with pytest.raises(ValueError, match="cannot exceed 128"):
            _validate_password("Aa1!" + "x" * 126)

    def test_forbidden_characters_rejected(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            _validate_password("Abcdefg1!;")

    def test_repeated_characters_rejected(self):
        with pytest.raises(ValueError, match="repeated characters"):
            _validate_password("Baaaa1!cdef")

    def test_keyboard_pattern_rejected(self):
        with pytest.raises(ValueError, match="keyboard patterns"):
            _validate_password("Qwerty1!abc")

    def test_common_password_rejected(self, monkeypatch):
        # No real common password satisfies the earlier composition rules, so the
        # common-password branch is only reachable by injecting the set.
        password = "Str0ng!Passw0rd"
        monkeypatch.setattr(user_module, "_COMMON_PASSWORDS", frozenset({password.lower()}))
        with pytest.raises(ValueError, match="too common"):
            _validate_password(password)

    def test_strong_password_accepted(self):
        assert _validate_password("Str0ng!Passw0rd") == "Str0ng!Passw0rd"


class TestKronicleUserNameFields:
    def test_explicit_none_full_name_kept(self):
        u = KronicleUser(name="test.user", email="user@example.com", full_name=None)
        assert u.full_name is None

    def test_invalid_full_name_rejected(self):
        with pytest.raises(ValueError):
            KronicleUser(name="test.user", email="user@example.com", full_name="x!")

    def test_valid_full_name_accepted(self):
        u = KronicleUser(name="test.user", email="user@example.com", full_name="Test User")
        assert u.full_name == "Test User"


class TestKronicleUserFlags:
    def test_is_active_default_is_none(self):
        u = KronicleUser(name="test.user", email="user@example.com")
        assert u.is_active is None

    def test_is_active_false_is_kept(self):
        u = KronicleUser(name="test.user", email="user@example.com", is_active=False)
        assert u.is_active is False

    def test_is_active_true_is_normalized_to_none(self):
        u = KronicleUser(name="test.user", email="user@example.com", is_active=True)
        assert u.is_active is None

    def test_is_su_default_is_none(self):
        u = KronicleUser(name="test.user", email="user@example.com")
        assert u.is_su is None

    def test_is_su_true_is_kept(self):
        u = KronicleUser(name="test.user", email="user@example.com", is_su=True)
        assert u.is_su is True

    def test_is_su_false_is_normalized_to_none(self):
        u = KronicleUser(name="test.user", email="user@example.com", is_su=False)
        assert u.is_su is None


class TestKronicleUserSerialization:
    def test_model_dump_skips_flag_defaults(self):
        u = KronicleUser(name="test.user", email="user@example.com")
        d = u.model_dump()
        assert "is_active" not in d
        assert "is_su" not in d

    def test_model_dump_keeps_is_active_false(self):
        u = KronicleUser(name="test.user", email="user@example.com", is_active=False)
        assert u.model_dump()["is_active"] is False

    def test_model_dump_is_active_true_pops_field(self):
        # White-box: validate_is_active can never return True, so set it directly
        # to exercise the `if self.is_active:` pop branch.
        u = KronicleUser(name="test.user", email="user@example.com")
        u.is_active = True
        assert "is_active" not in u.model_dump()

    def test_model_dump_keeps_is_su_true(self):
        u = KronicleUser(name="test.user", email="user@example.com", is_su=True)
        assert u.model_dump()["is_su"] is True

    def test_model_dump_json(self):
        u = KronicleUser(name="test.user", email="user@example.com")
        assert "test.user" in u.model_dump_json()

    def test_str(self):
        u = KronicleUser(name="test.user", email="user@example.com")
        assert str(u).startswith("User ")
