from __future__ import annotations

from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase


class KronicleZone(KronicleRbacBase):
    pass


if __name__ == "__main__":  # pragma: no-cover
    from uuid import uuid4

    from kronicle_sdk.utils.log import log_d

    here = "kron_zone.tests"
    zone = KronicleZone(id=uuid4(), name="test.zone", details={"test": True})
    log_d(here, "zone", zone)
    log_d(here, "zone", f"{zone}")
