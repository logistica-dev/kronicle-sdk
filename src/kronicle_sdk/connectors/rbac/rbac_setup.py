# kronicle_sdk/connectors/rbac/rbac_setup.py
from typing import Any
from uuid import UUID

from kronicle_sdk.connectors.auth.kronicle_auth import KronicleUsrLogin
from kronicle_sdk.models.data.kronicle_payload import KroniclePayload
from kronicle_sdk.models.rbac.kronicle_group import KronicleGroup
from kronicle_sdk.models.rbac.kronicle_role import KronicleRole
from kronicle_sdk.models.rbac.kronicle_user import KronicleUser
from requests import put


class KronicleRbac(KronicleUsrLogin):
    def __init__(self, url: str, usr: str, pwd: str) -> None:
        super().__init__(url, usr, pwd)

    @property
    def prefix(self) -> str:
        return "/rbac/v1"

    # ----------------------------------------------------------------------------------------------
    # Users
    # ----------------------------------------------------------------------------------------------

    def get_all_users(self, *, include_inactive: bool = False) -> list[KronicleUser]:
        route_get_users = "/users?include_inactive=1" if include_inactive else "/users"
        list_users = self.get(route=route_get_users)
        return [KronicleUser(**usr) for usr in list_users]

    def get_user_by_id(self, *, user_id: UUID) -> KronicleUser | None:
        res = self.get(route=f"/users/{user_id}")
        return KronicleUser(**res) if res else None

    def get_user_by_email(self, *, email: str) -> KronicleUser | None:
        res = self.get(route=f"/users?email={email}")
        return KronicleUser(**res) if res else None

    def get_user_by_name(self, *, name: str) -> KronicleUser | None:
        res = self.get(route=f"/users?name={name}")
        return KronicleUser(**res) if res else None

    def get_user_by_orcid(self, *, orcid: str) -> KronicleUser | None:
        res = self.get(route=f"/users?orcid={orcid}")
        return KronicleUser(**res) if res else None

    def create_user(self, user: KronicleUser) -> KronicleUser:
        usr = self.post(route="/users", body=user.model_dump())
        return KronicleUser(**usr)

    def patch_user(self, user: KronicleUser) -> KronicleUser:
        usr = self.patch(route=f"/users/{user.id}", body=user.model_dump())
        return KronicleUser(**usr)

    def deactivate_user(self, *, user_id: UUID) -> KronicleUser:
        usr = self.delete(route=f"/users/{user_id}")
        return KronicleUser(**usr)

    def delete_user(self, *, user_id: UUID) -> KronicleUser:
        usr = self.delete(route=f"/users/{user_id}?remove=true")
        return KronicleUser(**usr)

    # ----------------------------------------------------------------------------------------------
    # Groups
    # ----------------------------------------------------------------------------------------------

    def get_all_groups(self) -> list[KronicleGroup]:
        groups = self.get(route="/groups")
        return [KronicleGroup(**g) for g in groups]

    def get_group_by_id(self, *, group_id: UUID) -> KronicleGroup | None:
        res = self.get(route=f"/groups/{group_id}")
        return KronicleGroup(**res) if res else None

    def get_group_by_name(self, *, name: str) -> KronicleGroup | None:
        res = self.get(route=f"/groups?name={name}")
        return KronicleGroup(**res) if res else None

    def create_group(self, group: KronicleGroup) -> KronicleGroup:
        res = self.post(route="/groups", body=group.model_dump())
        return KronicleGroup(**res)

    def patch_group(self, group: KronicleGroup) -> KronicleGroup:
        res = self.patch(route=f"/groups/{group.id}", body=group.model_dump())
        return KronicleGroup(**res)

    def delete_group(self, *, group_id: UUID, force: bool = False) -> KronicleGroup | None:
        route = f"/groups/{group_id}?force=true" if force else f"/groups/{group_id}"
        res = self.delete(route=route)
        return KronicleGroup(**res) if res else None

    def get_users_from_group(self, *, group_id: UUID) -> list[KronicleUser]:
        return self.get(route=f"/groups/{group_id}/users")

    def add_user_to_group(self, *, group_id: UUID, user_id: UUID) -> dict:
        return self.post(route=f"/groups/{group_id}/users?user_id={user_id}")

    def remove_user_from_group(self, *, group_id: UUID, user_id: UUID) -> dict:
        return self.delete(route=f"/groups/{group_id}/users/{user_id}")

    # ----------------------------------------------------------------------------------------------
    # Roles
    # ----------------------------------------------------------------------------------------------

    def get_all_roles(self) -> list[KronicleRole]:
        roles = self.get(route="/roles")
        return [KronicleRole(**r) for r in roles]

    def get_role_by_id(self, *, role_id: UUID) -> KronicleRole | None:
        res = self.get(route=f"/roles/{role_id}")
        return KronicleRole(**res) if res else None

    def get_role_by_name(self, *, name: str) -> KronicleRole | None:
        res = self.get(route=f"/roles?name={name}")
        return KronicleRole(**res) if res else None

    def create_role(self, role: KronicleRole) -> KronicleRole:
        res = self.post(route="/roles", body=role.model_dump())
        return KronicleRole(**res)

    def patch_role(self, role: KronicleRole) -> KronicleRole:
        res = self.patch(route=f"/roles/{role.id}", body=role.model_dump())
        return KronicleRole(**res)

    def delete_role(self, *, role_id: UUID, force: bool = False) -> KronicleRole | None:
        route = f"/roles/{role_id}?force=true" if force else f"/roles/{role_id}"
        res = self.delete(route=route)
        return KronicleRole(**res) if res else None

    def put(
        self,
        route: str,
        body: KroniclePayload | dict | None = None,
        *,
        prefix: str | None = None,
        **kwargs,
    ) -> Any:
        """Override parent's put() to allow bodyless PUT for role assignments."""
        return self._request(put, route=route, body=body, prefix=prefix, timeout=self.timeout, **kwargs)

    def assign_role_to_user(self, *, role_id: UUID, user_id: UUID) -> dict:
        return self.put(route=f"/users/{user_id}/roles/{role_id}")

    def assign_role_to_group(self, *, role_id: UUID, group_id: UUID) -> dict:
        return self.put(route=f"/groups/{group_id}/roles/{role_id}")

    def remove_role_from_user(self, *, role_id: UUID, user_id: UUID) -> dict:
        return self.delete(route=f"/users/{user_id}/roles/{role_id}")

    def remove_role_from_group(self, *, role_id: UUID, group_id: UUID) -> dict:
        return self.delete(route=f"/groups/{group_id}/roles/{role_id}")

    # ----------------------------------------------------------------------------------------------
    # Relationship checks
    # ----------------------------------------------------------------------------------------------

    def check_user_has_role(self, *, user_id: UUID, role_id: UUID, indirect: bool = False) -> dict:
        params = {"indirect": "1"} if indirect else None
        return self.get(route=f"/users/{user_id}/roles/{role_id}", params=params)

    def check_group_has_role(self, *, group_id: UUID, role_id: UUID, indirect: bool = False) -> dict:
        params = {"indirect": "1"} if indirect else None
        return self.get(route=f"/groups/{group_id}/roles/{role_id}", params=params)

    def list_role_subjects(self, *, role_id: UUID, indirect: bool = False) -> dict:
        params = {"indirect": "1"} if indirect else None
        return self.get(route=f"/roles/{role_id}/subjects", params=params)

    def get_users_for_role(self, *, role_id: UUID, indirect: bool = False) -> list[str]:
        data = self.list_role_subjects(role_id=role_id, indirect=indirect)
        users: list[str] = data.get("users", [])
        if indirect:
            users.extend(data.get("indirect_users", []))
        return users

    def get_groups_for_role(self, *, role_id: UUID, indirect: bool = False) -> list[str]:
        data = self.list_role_subjects(role_id=role_id, indirect=indirect)
        return data.get("groups", [])

    def check_user_in_group(self, *, user_id: UUID, group_id: UUID, indirect: bool = False) -> dict:
        params = {"indirect": "1"} if indirect else None
        return self.get(route=f"/users/{user_id}/groups/{group_id}", params=params)
