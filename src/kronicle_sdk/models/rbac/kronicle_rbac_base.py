from __future__ import annotations

import re
from ast import TypeVar
from typing import Any, ClassVar, Self
from uuid import UUID, uuid4

from kronicle_sdk.utils.str_utils import ensure_uuid4, serialize
from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


class KronicleRbacBase(BaseModel):
    _name_regex: ClassVar[str] = r"[A-Za-z][A-Za-z0-9_ .-]{3,63}"

    id: UUID = Field(default_factory=uuid4)
    name: str | None = None
    details: dict[str, Any] | None = None

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v: str | UUID | None) -> UUID:
        if not v:
            return uuid4()
        return ensure_uuid4(v)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.fullmatch(cls._name_regex, v):
            raise ValueError(
                "Name must start with a letter, be 4-64 characters long, "
                "and only contain letters, digits, '_', '.', '-', or space"
            )
        return v

    def model_dump(self, *args, exclude_none=True, **kwargs) -> dict:
        d = super().model_dump(*args, exclude_none=exclude_none, **kwargs)
        return serialize(d, exclude_none=exclude_none)

    def model_dump_json(self, *args, exclude_none=True, **kwargs) -> str:
        return str(self.model_dump(*args, exclude_none=exclude_none, **kwargs))

    def to_json(self) -> dict:
        return self.model_dump()

    @classmethod
    def from_json(cls, d: dict) -> Self:
        return cls.model_validate(d, from_attributes=True)

    def __str__(self) -> str:
        cls_name = self.__class__.__name__
        if cls_name.startswith("Kronicle"):
            cls_name = "K" + cls_name[8:]
        return f"{cls_name} {self.model_dump(exclude_none=True)}"

    @classmethod
    def _extract_field(cls, d: dict, field_name: str, T: type):
        if not (field := d.get(field_name)):
            raise ValueError(f"'{field_name}' not found in {d}")
        return T.from_json(field)
