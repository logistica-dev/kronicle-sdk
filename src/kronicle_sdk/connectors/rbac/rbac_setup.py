# kronicle_sdk/connectors/rbac/rbac_setup.py
from typing import Any
from uuid import UUID

from requests import put

from kronicle_sdk.connectors.auth.kronicle_auth import KronicleUsrLogin
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.rbac.kronicle_access_profile import (
    KronicleAccessProfile,
    KronicleChannelAccess,
    KronicleZoneAccess,
)
from kronicle_sdk.models.rbac.kronicle_group import KronicleGroup
from kronicle_sdk.models.rbac.kronicle_policy import (
    KronicleChannelPolicy,
    KronicleRowAccess,
    KronicleRowPolicy,
    KronicleZonePolicy,
)
from kronicle_sdk.models.rbac.kronicle_role import KronicleRole
from kronicle_sdk.models.rbac.kronicle_user import KronicleUser
from kronicle_sdk.utils.log import log_d


class KronicleRbac(KronicleUsrLogin):
    def __init__(self, url: str, usr: str, pwd: str) -> None:
        super().__init__(url, usr, pwd)

    @property
    def prefix(self) -> str:
        return "/rbac/v1"

    # ----------------------------------------------------------------------------------------------
    # Users
    # ----------------------------------------------------------------------------------------------

    def list_users(self, *, include_inactive: bool = False) -> list[KronicleUser]:
        res = self.get(route="/users?include_inactive=1" if include_inactive else "/users")
        return [KronicleUser.from_json(usr) for usr in res]

    def get_user_by_id(self, *, user_id: UUID) -> KronicleUser | None:
        res = self.get(route=f"/users/{user_id}")
        return KronicleUser.from_json(res) if res else None

    def get_user_by_email(self, *, email: str) -> KronicleUser | None:
        res = self.get(route=f"/users?email={email}")
        return KronicleUser.from_json(res) if res else None

    def get_user_by_name(self, *, name: str) -> KronicleUser | None:
        res = self.get(route=f"/users?name={name}")
        return KronicleUser.from_json(res) if res else None

    def get_user_by_orcid(self, *, orcid: str) -> KronicleUser | None:
        res = self.get(route=f"/users?orcid={orcid}")
        return KronicleUser.from_json(res) if res else None

    def create_user(self, user: KronicleUser) -> KronicleUser:
        res = self.post(route="/users", body=user.model_dump())
        return KronicleUser.from_json(res)

    def patch_user(self, user: KronicleUser) -> KronicleUser:
        res = self.patch(route=f"/users/{user.id}", body=user.model_dump())
        return KronicleUser.from_json(res)

    def deactivate_user(self, *, user_id: UUID) -> KronicleUser:
        res = self.delete(route=f"/users/{user_id}")
        return KronicleUser.from_json(res)

    def delete_user(self, *, user_id: UUID) -> KronicleUser:
        res = self.delete(route=f"/users/{user_id}?remove=true")
        return KronicleUser.from_json(res)

    # ----------------------------------------------------------------------------------------------
    # Groups
    # ----------------------------------------------------------------------------------------------

    def list_groups(self) -> list[KronicleGroup]:
        res = self.get(route="/groups")
        return [KronicleGroup.from_json(r) for r in res]

    def get_group_by_id(self, *, group_id: UUID) -> KronicleGroup:
        res = self.get(route=f"/groups/{group_id}")
        return KronicleGroup.from_json(res)

    def get_group_by_name(self, *, name: str) -> KronicleGroup:
        res = self.get(route=f"/groups?name={name}")
        return KronicleGroup.from_json(res)

    def create_group(self, group: KronicleGroup) -> KronicleGroup:
        res = self.post(route="/groups", body=group.model_dump())
        return KronicleGroup.from_json(res)

    def patch_group(self, group: KronicleGroup) -> KronicleGroup:
        res = self.patch(route=f"/groups/{group.id}", body=group.model_dump())
        return KronicleGroup.from_json(res)

    def delete_group(self, *, group_id: UUID, force: bool = False) -> KronicleGroup:
        res = self.delete(route=f"/groups/{group_id}?force=true" if force else f"/groups/{group_id}")
        return KronicleGroup.from_json(res)

    def get_users_from_group(self, *, group_id: UUID) -> list[KronicleUser]:
        res = self.get(route=f"/groups/{group_id}/users")
        return [KronicleUser.from_json(r) for r in res] if res else []

    def add_user_to_group(self, *, group_id: UUID, user_id: UUID) -> dict:
        return self.post(route=f"/groups/{group_id}/users?user_id={user_id}")

    def remove_user_from_group(self, *, group_id: UUID, user_id: UUID) -> dict:
        return self.delete(route=f"/groups/{group_id}/users/{user_id}")

    # ----------------------------------------------------------------------------------------------
    # Roles
    # ----------------------------------------------------------------------------------------------

    def list_roles(self) -> list[KronicleRole]:
        roles = self.get(route="/roles")
        return [KronicleRole.from_json(r) for r in roles]

    def get_role_by_id(self, *, role_id: UUID) -> KronicleRole:
        res = self.get(route=f"/roles/{role_id}")
        return KronicleRole.from_json(res)

    def get_role_by_name(self, *, name: str) -> KronicleRole:
        res = self.get(route=f"/roles?name={name}")
        return KronicleRole.from_json(res)

    def create_role(self, role: KronicleRole) -> KronicleRole:
        res = self.post(route="/roles", body=role.model_dump())
        return KronicleRole.from_json(res)

    def patch_role(self, role: KronicleRole) -> KronicleRole:
        res = self.patch(route=f"/roles/{role.id}", body=role.model_dump())
        return KronicleRole.from_json(res)

    def delete_role(self, *, role_id: UUID, force: bool = False) -> KronicleRole:
        route = f"/roles/{role_id}?force=true" if force else f"/roles/{role_id}"
        res = self.delete(route=route)
        return KronicleRole.from_json(res)

    def put(
        self,
        route: str,
        body: KronicleChannel | dict | None = None,
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

    # ----------------------------------------------------------------------------------------------
    # Access Profiles (preemptive scoped roles)
    # ----------------------------------------------------------------------------------------------

    def list_access_profiles(self) -> dict[str, list[KronicleAccessProfile]]:
        res: dict[str, list[dict]] = self.get(route="/access-profiles")
        result = {}
        for resource_str, KronicleAccess in [
            ("zone", KronicleZoneAccess),
            ("channel", KronicleChannelAccess),
            ("row", KronicleRowAccess),
        ]:
            access_list = []
            for v in res.get(resource_str) or []:
                access_list.append(KronicleAccess.from_json(v))
            result[resource_str] = access_list
        return result

    # ----------------------------------------------------------------------------------------------
    # Zone Access Profiles (preemptive scoped roles)
    # ----------------------------------------------------------------------------------------------

    def create_zone_access_profile(self, access: KronicleZoneAccess) -> KronicleZoneAccess:
        res = self.post(
            route="/access-profiles/zones",
            body=access.model_dump(),
        )
        return KronicleZoneAccess.from_json(res)

    def list_zone_access_profiles(self) -> list[KronicleZoneAccess]:
        res = self.get(route="/access-profiles/zones")
        return [KronicleZoneAccess.from_json(r) for r in res] if res else []

    def get_zone_access_profile(self, *, profile_id: UUID) -> KronicleZoneAccess:
        res = self.get(route=f"/access-profiles/zones/{profile_id}")
        return KronicleZoneAccess.from_json(res)

    def patch_zone_access_profile(self, access_profile: KronicleZoneAccess) -> KronicleZoneAccess:
        res = self.patch(route=f"/access-profiles/zones/{access_profile.id}", body=access_profile.model_dump())
        return KronicleZoneAccess.from_json(res)

    def delete_zone_access_profile(self, *, profile_id: UUID) -> KronicleZoneAccess:
        res = self.delete(route=f"/access-profiles/zones/{profile_id}")
        return KronicleZoneAccess.from_json(res)

    # ----------------------------------------------------------------------------------------------
    # Channel Access Profiles (preemptive scoped roles)
    # ----------------------------------------------------------------------------------------------

    def create_channel_access_profile(self, access_profile: KronicleChannelAccess) -> KronicleChannelAccess:
        res = self.post(route="/access-profiles/channels", body=access_profile.model_dump())
        # log_d("create_channel_access_profile", res)
        return KronicleChannelAccess.from_json(res)

    def list_channel_access_profiles(self) -> list[KronicleChannelAccess]:
        res = self.get(route="/access-profiles/channels")
        # log_d("list_channel_access_profiles", res)
        return [KronicleChannelAccess.from_json(r) for r in res] if res else []

    def get_channel_access_profile(self, *, profile_id: UUID) -> KronicleChannelAccess:
        res = self.get(route=f"/access-profiles/channels/{profile_id}")
        return KronicleChannelAccess.from_json(res)

    def patch_channel_access_profile(self, access_profile: KronicleChannelAccess) -> KronicleChannelAccess:
        res = self.patch(route=f"/access-profiles/channels/{access_profile.id}", body=access_profile.model_dump())
        return KronicleChannelAccess.from_json(res)

    def delete_channel_access_profile(self, *, profile_id: UUID) -> KronicleChannelAccess:
        res = self.delete(route=f"/access-profiles/channels/{profile_id}")
        return KronicleChannelAccess.from_json(res)

    # ----------------------------------------------------------------------------------------------
    # Row Access Profiles
    # ----------------------------------------------------------------------------------------------

    def create_row_access_profile(self, access_profile: KronicleRowAccess) -> KronicleRowAccess:
        log_d("create_row_access_profile", access_profile)
        res = self.post(route="/access-profiles/rows", body=access_profile.model_dump())
        return KronicleRowAccess.from_json(res)

    def list_row_access_profiles(self) -> list[KronicleRowAccess]:
        res = self.get(route="/access-profiles/rows")
        return [KronicleRowAccess.from_json(r) for r in res] if res else []

    def get_row_access_profile(self, *, profile_id: UUID) -> KronicleRowAccess:
        res = self.get(route=f"/access-profiles/rows/{profile_id}")
        return KronicleRowAccess.from_json(res)

    def patch_row_access_profile(self, access_profile: KronicleRowAccess) -> KronicleRowAccess:
        res = self.patch(route=f"/access-profiles/rows/{access_profile.id}", body=access_profile.model_dump())
        return KronicleRowAccess.from_json(res)

    def delete_row_access_profile(self, *, profile_id: UUID) -> KronicleRowAccess:
        res = self.delete(route=f"/access-profiles/rows/{profile_id}")
        return KronicleRowAccess.from_json(res)

    # ----------------------------------------------------------------------------------------------
    # Policies
    # ----------------------------------------------------------------------------------------------

    def list_policies(
        self,
    ) -> dict[str, list[KronicleZonePolicy | KronicleChannelPolicy | KronicleRowPolicy]]:
        res = self.get(route="/policies")
        return {
            resource: [cls(**p) for p in res.get(resource, [])]
            for resource, cls in (
                ("zone", KronicleZonePolicy),
                ("channel", KronicleChannelPolicy),
                ("row", KronicleRowPolicy),
            )
        }

    # ----------------------------------------------------------------------------------------------
    # Zone Policies
    # ----------------------------------------------------------------------------------------------

    def create_zone_policy(self, zone_policy: KronicleZonePolicy) -> KronicleZonePolicy:
        log_d("create_zone_policy", zone_policy)
        res = self.post(route="/policies/zones", body=zone_policy.model_dump())
        return KronicleZonePolicy.from_json(res)

    def list_zone_policies(self) -> list[KronicleZonePolicy]:
        res = self.get(route="/policies/zones")
        return [KronicleZonePolicy.from_json(r) for r in res] if res else []

    def get_zone_policy(self, *, policy_id: UUID) -> KronicleZonePolicy:
        res = self.get(route=f"/policies/zones/{policy_id}")
        return KronicleZonePolicy.from_json(res)

    def delete_zone_policy(self, *, policy_id: UUID) -> KronicleZonePolicy:
        res = self.delete(route=f"/policies/zones/{policy_id}")
        return KronicleZonePolicy.from_json(res)

    def patch_zone_policy(self, zone_policy: KronicleZonePolicy) -> KronicleZonePolicy:
        res = self.patch(route=f"/policies/zones/{zone_policy.id}", body=zone_policy.model_dump())
        return KronicleZonePolicy.from_json(res)

    # ----------------------------------------------------------------------------------------------
    # Channel Policies
    # ----------------------------------------------------------------------------------------------

    def create_channel_policy(self, channel_policy: KronicleChannelPolicy) -> KronicleChannelPolicy:
        res = self.post(route="/policies/channels", body=channel_policy.model_dump())
        return KronicleChannelPolicy.from_json(res)

    def list_channel_policies(self) -> list[KronicleChannelPolicy]:
        res = self.get(route="/policies/channels")
        return [KronicleChannelPolicy.from_json(r) for r in res] if res else []

    def get_channel_policy(self, *, policy_id: UUID) -> KronicleChannelPolicy:
        res = self.get(route=f"/policies/channels/{policy_id}")
        return KronicleChannelPolicy.from_json(res)

    def delete_channel_policy(self, *, policy_id: UUID) -> KronicleChannelPolicy:
        res = self.delete(route=f"/policies/channels/{policy_id}")
        return KronicleChannelPolicy.from_json(res)

    def patch_channel_policy(self, channel_policy: KronicleChannelPolicy) -> KronicleChannelPolicy:
        res = self.patch(route=f"/policies/channels/{channel_policy.id}", body=channel_policy.model_dump())
        return KronicleChannelPolicy.from_json(res)

    # ----------------------------------------------------------------------------------------------
    # Row Policies
    # ----------------------------------------------------------------------------------------------

    def create_row_policy(self, row_policy: KronicleRowPolicy) -> KronicleRowPolicy:
        res = self.post(route="/policies/rows", body=row_policy.model_dump())
        return KronicleRowPolicy.from_json(res)

    def list_row_policies(self) -> list[KronicleRowPolicy]:
        res = self.get(route="/policies/rows")
        return [KronicleRowPolicy.from_json(r) for r in res] if res else []

    def get_row_policy(self, *, policy_id: UUID) -> KronicleRowPolicy:
        res = self.get(route=f"/policies/rows/{policy_id}")
        return KronicleRowPolicy.from_json(res)

    def delete_row_policy(self, *, policy_id: UUID) -> KronicleRowPolicy:
        res = self.delete(route=f"/policies/rows/{policy_id}")
        return KronicleRowPolicy.from_json(res)

    def patch_row_policy(self, row_policy: KronicleRowPolicy) -> KronicleRowPolicy:
        res = self.patch(route=f"/policies/rows/{row_policy.id}", body=row_policy.model_dump())
        return KronicleRowPolicy.from_json(res)
