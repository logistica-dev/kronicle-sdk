from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator

from kronicle_sdk.utils.dict_utils import skip_nones
from kronicle_sdk.utils.str_utils import uuid_to_str

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
_NAME_REGEX = r"[A-Za-z][A-Za-z0-9_ .@-]{3,63}"
_PASSWORD_FORBIDDEN = re.compile(r'[\'"\\$`;&|<>#\n\r\t]')
_PASSWORD_REPEATED = re.compile(r"(.)\1{3,}")


def _validate_password(password: str | None) -> str | None:  # noqa: C901
    """
    This reflects the default constraints implemented in the Kronicle server
    for the Kronicle user's password.
    """
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


def _validate_name(v: str | None) -> str | None:
    if v is None:
        return v
    if not re.fullmatch(_NAME_REGEX, v):
        raise ValueError(
            "Username must start with a letter, be 4–64 characters long, "
            "and only contain letters, digits, '_', '.', '-', '@', or space"
        )
    return v


class KronicleUser(BaseModel):
    email: str
    id: UUID | None = None
    password: str | None = None
    name: str | None = None
    orcid: str | None = None
    full_name: str | None = None
    details: dict[str, Any] | None = None

    @field_validator("password")
    @classmethod
    def validate_password_syntax(cls, v: str | None) -> str | None:
        return _validate_password(v)

    @field_validator("name", "full_name")
    @classmethod
    def validate_name_syntax(cls, v: str | None) -> str | None:
        return _validate_name(v)

    def to_json(self) -> dict:
        return skip_nones(
            {
                "id": uuid_to_str(self.id),
                "email": self.email,
                "name": self.name,
                "orcid": self.orcid,
                "full_name": self.full_name,
                "password": self.password,
            }
        )

    def __str__(self) -> str:
        return f"User {self.to_json()}"
