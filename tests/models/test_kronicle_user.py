# tests/models/test_kronicle_user.py
import pytest

from kronicle_sdk.models.rbac.kronicle_user import KronicleUser


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
