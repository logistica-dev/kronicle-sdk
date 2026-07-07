from __future__ import annotations

import re
from json import dumps
from typing import ClassVar

from pydantic import field_validator

from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase
from kronicle_sdk.utils.dict_utils import skip_nones

_COMMON_PASSWORDS = frozenset(
    {
        "password",
        "motdepasse",
        "123456",
        "qwerty",
        "letmein",
        "welcome",
        "admin",
        "monkey",
        "sunshine",
        "password1",
        "123123",
    }
)
_KEYBOARD_PATTERNS = [
    "qwerty",
    "asdfgh",
    "zxcvbn",
    "123456",
    "654321",
    "!@#$%^",
    "1qaz",
    "2wsx",
    "3edc",
    "4rfv",
    "5tgb",
]
_SPECIAL_CHARS = "!@%^*()_+-=[]{}|:,.?"
_PASSWORD_FORBIDDEN = re.compile(r'[\'"\\$`;&|<>#\n\r\t]')
_PASSWORD_REPEATED = re.compile(r"(.)\1{3,}")


def _validate_password(password: str | None) -> str | None:  # noqa: C901
    if password is None:
        return None
    if not password:
        raise ValueError("Password cannot be empty")
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters")
    if len(password) > 128:
        raise ValueError("Password cannot exceed 128 characters")
    if _PASSWORD_FORBIDDEN.search(password):
        raise ValueError("Password cannot contain forbidden characters: '\"\\$`;&|<># (and whitespace)")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(f"[{re.escape(_SPECIAL_CHARS)}]", password):
        raise ValueError(f"Password must contain at least one special character: {_SPECIAL_CHARS}")
    if password.lower() in _COMMON_PASSWORDS:
        raise ValueError("Password is too common")
    if _PASSWORD_REPEATED.search(password):
        raise ValueError("Password contains too many repeated characters")
    pwd_lower = password.lower()
    for pattern in _KEYBOARD_PATTERNS:
        if pattern in pwd_lower:
            raise ValueError("Password contains common keyboard patterns")
    return password


class KronicleUser(KronicleRbacBase):
    _name_regex: ClassVar[str] = r"[A-Za-z][A-Za-z0-9_ .@-]{3,63}"

    name: str | None = None
    email: str
    password: str | None = None
    orcid: str | None = None
    full_name: str | None = None
    is_active: bool | None = None
    is_su: bool | None = None

    @field_validator("password")
    @classmethod
    def validate_password_syntax(cls, v: str | None) -> str | None:
        return _validate_password(v)

    @field_validator("name", "full_name")
    @classmethod
    def validate_name_syntax(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.fullmatch(cls._name_regex, v):
            raise ValueError(
                "Username must start with a letter, be 4–64 characters long, "
                "and only contain letters, digits, '_', '.', '-', '@', or space"
            )
        return v

    @field_validator("is_active")
    @classmethod
    def validate_is_active(cls, v: bool | None) -> bool | None:
        return False if v is False else None

    @field_validator("is_su")
    @classmethod
    def validate_is_su(cls, v: bool | None) -> bool | None:
        return True if v is True else None

    def model_dump(self, *args, exclude_none=True, **kwargs) -> dict:
        d = super().model_dump(*args, exclude_none=exclude_none, **kwargs)

        if self.is_active:
            d.pop("is_active", None)
        if self.is_su:
            d["is_su"] = True
        else:
            d.pop("is_su", None)
        return skip_nones(d)

    def model_dump_json(self, *args, **kwargs) -> str:
        return dumps(self.model_dump(*args, **kwargs))

    def __str__(self) -> str:
        return f"User {self.model_dump_json()}"
