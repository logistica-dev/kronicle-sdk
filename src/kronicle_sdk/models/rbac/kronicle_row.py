from __future__ import annotations

from uuid import UUID

from pydantic import field_validator

from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase


class KronicleRow(KronicleRbacBase):
    # Override the base id (UUID) : here id is the timeseries BIGSERIAL row_id.
    id: int  # type: ignore
    channel_id: UUID
    # Internal CoreRow PK (UUID) assigned by the server once the row is materialised.
    core_row_id: UUID | None = None

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v) -> int:  # pyright: ignore[reportIncompatibleMethodOverride]
        if isinstance(v, int):
            return v
        raise ValueError("row id must be an integer")


if __name__ == "__main__":  # pragma: no cover
    from kronicle_sdk.utils.log import log_d

    here = "kron_zone.tests"

    row = KronicleRow(
        id=5, channel_id=UUID("a1205f1c-1f6e-4a9f-9a2f-8a2b0f6a7c9f"), name="test.row", details={"test": True}
    )
    log_d(here, "row", row)
    log_d(here, "row", f"{row}")
