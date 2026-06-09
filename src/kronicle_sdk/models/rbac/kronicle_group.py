from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator

from kronicle_sdk.utils.dict_utils import skip_nones
from kronicle_sdk.utils.str_utils import uuid_to_str

_NAME_REGEX = r"[A-Za-z][A-Za-z0-9_ .-]{3,63}"


def _validate_name(v: str | None) -> str | None:
    if v is None:
        return v
    if not re.fullmatch(_NAME_REGEX, v):
        raise ValueError(
            "Group name must start with a letter, be 4–64 characters long, "
            "and only contain letters, digits, '_', '.', '-', or space"
        )
    return v


class KronicleGroup(BaseModel):
    id: UUID | None = None
    name: str | None = None
    details: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def validate_name_syntax(cls, v: str | None) -> str | None:
        return _validate_name(v)

    def to_json(self) -> dict:
        return skip_nones({"id": uuid_to_str(self.id), "name": self.name, "details": self.details})

    def __str__(self) -> str:
        return f"Group {self.to_json()}"


if __name__ == "__main__":  # pragma: no-cover
    from uuid import uuid4

    from kronicle_sdk.utils.log import log_d

    here = "kron_group.tests"
    group = KronicleGroup(id=uuid4(), name="test.group")
    log_d(here, "group", group)
    log_d(here, "group", f"{group}")
