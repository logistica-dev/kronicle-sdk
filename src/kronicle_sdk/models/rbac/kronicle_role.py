from __future__ import annotations

from kronicle_sdk.models.rbac.kronicle_rbac_base import KronicleRbacBase
from kronicle_sdk.models.rbac.permission_sets import PermStr


class KronicleRole(KronicleRbacBase):
    name: str  # type:ignore
    description: str | None = None
    permissions: list[str] | list[PermStr] | None = None
    restrictions: list[str] | list[PermStr] | None = None

    def model_dump(self, *args, exclude_none=True, **kwargs) -> dict:
        d = super().model_dump(*args, exclude_none=exclude_none, **kwargs)
        if d.get("restrictions"):
            d.pop("restrictions")
        return d


if __name__ == "__main__":  # pragma: no-cover
    from kronicle_sdk.utils.log import log_d

    here = "kron_role.tests"
    role = KronicleRole(name="test.role", permissions=["channel:read"])
    log_d(here, "role", role)
    log_d(here, "role", f"{role}")
    log_d(here, "role.id", f"{role.id}")
