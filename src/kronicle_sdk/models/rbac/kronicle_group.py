from __future__ import annotations

from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase


class KronicleGroup(KronicleRbacBase):
    name: str
    pass


if __name__ == "__main__":  # pragma: no-cover
    from uuid import uuid4

    from kronicle_sdk.utils.log import log_d

    here = "kron_group.tests"
    group = KronicleGroup(id=uuid4(), name="test.group")
    log_d(here, "group", group)
    log_d(here, "group", f"{group}")
