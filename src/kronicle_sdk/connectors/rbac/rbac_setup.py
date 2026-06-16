# kronicle_sdk/connectors/rbac/rbac_identity_setup.py
from uuid import UUID

from kronicle_sdk.connectors.auth.kronicle_auth import KronicleUsrLogin
from kronicle_sdk.models.rbac.kronicle_group import KronicleGroup
from kronicle_sdk.models.rbac.kronicle_user import KronicleUser
from kronicle_sdk.utils.log import log_d


class KronicleRbac(KronicleUsrLogin):
    def __init__(self, url: str, usr: str, pwd: str) -> None:
        super().__init__(url, usr, pwd)

    @property
    def prefix(self) -> str:
        return "/rbac/v1"

    def get_all_users(self, *, include_inactive: bool = False) -> list[KronicleUser]:
        here = "get_all_users"
        if not include_inactive:
            list_users = self.get(route="/users")
        else:
            list_users = self.get(route="/users?include_inactive=1")
        log_d(here, list_users)
        return [KronicleUser(**usr) for usr in list_users]

    def get_user_by(
        self,
        email: str | None = None,
        name: str | None = None,
        id: UUID | None = None,
        orcid: str | None = None,
    ) -> KronicleUser | None:
        if email:
            user = self.get(route=f"/users?email={email}")
        elif name:
            user = self.get(route=f"/users?name={name}")
        elif id:
            user = self.get(route=f"/users/{id}")
        elif orcid:
            user = self.get(route=f"/users?orcid={orcid}")
        else:
            raise ValueError("One of the parameters should be given")
        return KronicleUser(**user) if user else None

    def create_user(self, user: KronicleUser) -> KronicleUser:
        usr = self.post(route="/users", body=user.to_json())
        return KronicleUser(**usr)

    def patch_user(self, user: KronicleUser) -> KronicleUser:
        usr = self.patch(route="/users", body=user.to_json())
        return KronicleUser(**usr)

    def deactivate_user(self, user: KronicleUser) -> KronicleUser:
        usr = self.delete(route="/users", body=user.to_json())
        return KronicleUser(**usr)

    def remove_user(self, user: KronicleUser) -> KronicleUser:
        usr = self.delete(route="/users?remove=true", body=user.to_json())
        return KronicleUser(**usr)

    def deactivate_user_by_id(self, id: UUID) -> KronicleUser:
        usr = self.delete(route=f"/users/{id}")
        return KronicleUser(**usr)

    def remove_user_by_id(self, id: UUID) -> KronicleUser:
        usr = self.delete(route=f"/users/{id}?remove=true")
        return KronicleUser(**usr)

    # ----------------------------------------------------------------------------------------------
    # Groups
    # ----------------------------------------------------------------------------------------------

    def create_group(self, group: KronicleGroup) -> KronicleGroup:
        res = self.post(route="/groups", body=group.to_json())
        return KronicleGroup(**res)

    def get_all_groups(self) -> list[KronicleGroup]:
        groups = self.get(route="/groups")
        return [KronicleGroup(**g) for g in groups]

    def get_group(self, group_id: UUID) -> KronicleGroup | None:
        res = self.get(route=f"/groups/{group_id}")
        return KronicleGroup(**res) if res else None

    def patch_group(self, group_id: UUID, group: KronicleGroup) -> KronicleGroup:
        res = self.patch(route=f"/groups/{group_id}", body=group.to_json())
        return KronicleGroup(**res)

    def delete_group(self, group_id: UUID) -> KronicleGroup | None:
        res = self.delete(route=f"/groups/{group_id}")
        return KronicleGroup(**res) if res else None

    def add_user_to_group(self, group_id: UUID, user_id: UUID) -> dict:
        return self.post(route=f"/groups/{group_id}/users?user_id={user_id}")

    def remove_user_from_group(self, group_id: UUID, user_id: UUID) -> dict:
        return self.delete(route=f"/groups/{group_id}/users/{user_id}")
