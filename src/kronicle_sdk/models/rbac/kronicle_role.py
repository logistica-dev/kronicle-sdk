from __future__ import annotations

from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase


class KronicleRole(KronicleRbacBase):
    description: str | None = None
    permissions: list[str] | None = None
    restrictions: list[str] | None = None


if __name__ == "__main__":  # pragma: no-cover
    from kronicle_sdk.utils.log import log_d

    here = "kron_role.tests"
    role = KronicleRole(name="test.role", permissions=["channel:read"])
    log_d(here, "role", role)
    log_d(here, "role", f"{role}")
    log_d(here, "role.id", f"{role.id}")
