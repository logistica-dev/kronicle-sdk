from __future__ import annotations

from uuid import UUID

from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase


class KronicleRow(KronicleRbacBase):
    id: UUID  # type: ignore
    channel_id: UUID


if __name__ == "__main__":  # pragma: no-cover
    from uuid import uuid4

    from kronicle_sdk.utils.log import log_d

    here = "kron_zone.tests"
    row = KronicleRow(id=uuid4(), channel_id=uuid4(), name="test.row", details={"test": True})
    log_d(here, "row", row)
    log_d(here, "row", f"{row}")
