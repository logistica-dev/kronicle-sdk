from typing import Any
from uuid import UUID

from pydantic import BaseModel

from kronicle.utils.dict_utils import skip_nones


class KronicleUser(BaseModel):
    email: str
    id: UUID | None = None
    password: str | None = None
    name: str | None = None
    orcid: str | None = None
    full_name: str | None = None
    details: dict[str, Any] | None = None

    def to_json(self) -> dict:
        return skip_nones(
            {
                "id": str(self.id),
                "email": self.email,
                "name": self.name,
                "orcid": self.orcid,
                "full_name": self.full_name,
                "password": self.password,
            }
        )

    def __str__(self) -> str:
        return f"User {self.to_json()}"
