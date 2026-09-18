# kronicle_sdk/connectors/rbac/rbac_setup.py
from typing import Any
from uuid import UUID

from requests import put

from kronicle_sdk.connectors.abc_connector import KronicleHTTPError
from kronicle_sdk.connectors.auth.kronicle_auth import KronicleUsrLogin
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.rbac.kronicle_access_profile import (
    KronicleAccessProfile,
    KronicleChannelAccess,
    KronicleZoneAccess,
)
from kronicle_sdk.models.rbac.kronicle_group import KronicleGroup
from kronicle_sdk.models.rbac.kronicle_permissions import KroniclePermissions
from kronicle_sdk.models.rbac.kronicle_policy import (
    KronicleChannelPolicy,
    KronicleRowAccess,
    KronicleRowPolicy,
    KronicleZonePolicy,
)
from kronicle_sdk.models.rbac.kronicle_role import KronicleRole
from kronicle_sdk.models.rbac.kronicle_user import KronicleUser
from kronicle_sdk.utils.log import log_d, log_i


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

    def get_user_by_id(self, user_id: UUID) -> KronicleUser | None:
        try:
            res = self.get(route=f"/users/{user_id}")
        except KronicleHTTPError as e:
            if e.status == 404:
                return None
            raise
        return KronicleUser.from_json(res) if res else None

    def get_user_by_email(self, email: str) -> KronicleUser | None:
        res = self.get(route=f"/users?email={email}")
        return KronicleUser.from_json(res) if res else None

    def get_user_by_name(self, name: str) -> KronicleUser | None:
        res = self.get(route=f"/users?name={name}")
        return KronicleUser.from_json(res) if res else None

    def get_user_by_orcid(self, orcid: str) -> KronicleUser | None:
        res = self.get(route=f"/users?orcid={orcid}")
        return KronicleUser.from_json(res) if res else None

    def get_user(self, user: KronicleUser) -> KronicleUser | None:
        if user.id and (existing := self.get_user_by_id(user_id=user.id)):
            return existing
        if user.email and (existing := self.get_user_by_email(email=user.email)):
            return existing
        if user.name and (existing := self.get_user_by_name(name=user.name)):
            return existing
        if user.orcid and (existing := self.get_user_by_orcid(orcid=user.orcid)):
            return existing
        return None

    def create_user(self, user: KronicleUser) -> KronicleUser:
        here = "create_user"
        if existing_user := self.get_user(user):
            log_i(
                here,
                f"User {existing_user.name or existing_user.email} [{existing_user.id}] already exists",
            )
            return existing_user
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

    def get_group_by_id(self, group_id: UUID) -> KronicleGroup | None:
        try:
            res = self.get(route=f"/groups/{group_id}")
        except KronicleHTTPError as e:
            if e.status == 404:
                return None
            raise
        return KronicleGroup.from_json(res) if res else None

    def get_group_by_name(self, name: str) -> KronicleGroup | None:
        res = self.get(route=f"/groups?name={name}")
        return KronicleGroup.from_json(res) if res else None

    def get_group(self, group: KronicleGroup) -> KronicleGroup | None:
        if group.id and (existing := self.get_group_by_id(group_id=group.id)):
            return existing
        if group.name and (existing := self.get_group_by_name(name=group.name)):
            return existing
        return None

    def create_group(self, group: KronicleGroup) -> KronicleGroup:
        here = "create_group"
        if existing_group := self.get_group(group):
            log_i(
                here,
                f"Group {existing_group.name} [{existing_group.id}] already exists",
            )
            return existing_group
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

    def get_role_by_id(self, role_id: UUID) -> KronicleRole | None:
        try:
            res = self.get(route=f"/roles/{role_id}")
        except KronicleHTTPError as e:
            if e.status == 404:
                return None
            raise
        return KronicleRole.from_json(res) if res else None

    def get_role_by_name(self, name: str) -> KronicleRole | None:
        res = self.get(route=f"/roles?name={name}")
        return KronicleRole.from_json(res) if res else None

    def get_role(self, role: KronicleRole) -> KronicleRole | None:
        if role.id and (existing := self.get_role_by_id(role_id=role.id)):
            return existing
        if role.name and (existing := self.get_role_by_name(name=role.name)):
            return existing
        return None

    def create_role(self, role: KronicleRole) -> KronicleRole:
        here = "create_role"
        if existing_role := self.get_role(role):
            log_i(here, f"Role {existing_role.name} [{existing_role.id}] already exists")
            return existing_role
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
    # Introspection: permissions
    # ----------------------------------------------------------------------------------------------

    def get_user_permissions(self, *, user_id: UUID) -> KroniclePermissions:
        res = self.get(route=f"/users/{user_id}/permissions")
        return KroniclePermissions.from_json(res)

    def get_group_permissions(self, *, group_id: UUID) -> KroniclePermissions:
        res = self.get(route=f"/groups/{group_id}/permissions")
        return KroniclePermissions.from_json(res)

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

    def get_zone_access_profile_by_name(self, *, name: str) -> KronicleZoneAccess | None:
        res = self.get(route=f"/access-profiles/zones?name={name}")
        return KronicleZoneAccess.from_json(res) if res else None

    def patch_zone_access_profile(self, access_profile: KronicleZoneAccess) -> KronicleZoneAccess:
        res = self.patch(
            route=f"/access-profiles/zones/{access_profile.id}",
            body=access_profile.model_dump(),
        )
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

    def get_channel_access_profile_by_name(self, *, name: str) -> KronicleChannelAccess | None:
        res = self.get(route=f"/access-profiles/channels?name={name}")
        return KronicleChannelAccess.from_json(res) if res else None

    def patch_channel_access_profile(self, access_profile: KronicleChannelAccess) -> KronicleChannelAccess:
        res = self.patch(
            route=f"/access-profiles/channels/{access_profile.id}",
            body=access_profile.model_dump(),
        )
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

    def get_row_access_profile_by_name(self, *, name: str) -> KronicleRowAccess | None:
        res = self.get(route=f"/access-profiles/rows?name={name}")
        return KronicleRowAccess.from_json(res) if res else None

    def patch_row_access_profile(self, access_profile: KronicleRowAccess) -> KronicleRowAccess:
        res = self.patch(
            route=f"/access-profiles/rows/{access_profile.id}",
            body=access_profile.model_dump(),
        )
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
        here = "create_zone_policy"
        if existing := self.get_zone_policy(zone_policy):
            log_i(
                here,
                f"Zone policy for {existing.subject.name or existing.subject.type} "
                f"on zone {existing.access_profile.zone.name} already exists",
            )
            return existing
        res = self.post(route="/policies/zones", body=zone_policy.model_dump())
        return KronicleZonePolicy.from_json(res)

    def list_zone_policies(self) -> list[KronicleZonePolicy]:
        res = self.get(route="/policies/zones")
        return [KronicleZonePolicy.from_json(r) for r in res] if res else []

    def get_zone_policy_by_id(self, *, policy_id: UUID) -> KronicleZonePolicy | None:
        try:
            res = self.get(route=f"/policies/zones/{policy_id}")
        except KronicleHTTPError as e:
            if e.status == 404:
                return None
            raise
        return KronicleZonePolicy.from_json(res) if res else None

    def get_zone_policy_by_name(self, *, name: str) -> KronicleZonePolicy | None:
        res = self.get(route=f"/policies/zones?name={name}")
        return KronicleZonePolicy.from_json(res) if res else None

    def get_zone_policy(self, zone_policy: KronicleZonePolicy) -> KronicleZonePolicy | None:
        if zone_policy.id and (existing := self.get_zone_policy_by_id(policy_id=zone_policy.id)):
            return existing
        if zone_policy.name and (existing := self.get_zone_policy_by_name(name=zone_policy.name)):
            return existing
        for existing in self.list_zone_policies():
            if existing.matches(zone_policy):
                return existing
        return None

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
        log_d("create_channel_policy", channel_policy)
        here = "create_channel_policy"
        if existing := self.get_channel_policy(channel_policy):
            log_i(
                here,
                f"Channel policy for {existing.subject.name or existing.subject.type} "
                f"on channel {existing.access_profile.channel.name} already exists",
            )
            return existing
        res = self.post(route="/policies/channels", body=channel_policy.model_dump())
        return KronicleChannelPolicy.from_json(res)

    def list_channel_policies(self) -> list[KronicleChannelPolicy]:
        res = self.get(route="/policies/channels")
        return [KronicleChannelPolicy.from_json(r) for r in res] if res else []

    def get_channel_policy_by_id(self, *, policy_id: UUID) -> KronicleChannelPolicy | None:
        try:
            res = self.get(route=f"/policies/channels/{policy_id}")
        except KronicleHTTPError as e:
            if e.status == 404:
                return None
            raise
        return KronicleChannelPolicy.from_json(res) if res else None

    def get_channel_policy_by_name(self, *, name: str) -> KronicleChannelPolicy | None:
        res = self.get(route=f"/policies/channels?name={name}")
        return KronicleChannelPolicy.from_json(res) if res else None

    def get_channel_policy(self, channel_policy: KronicleChannelPolicy) -> KronicleChannelPolicy | None:
        if channel_policy.id and (existing := self.get_channel_policy_by_id(policy_id=channel_policy.id)):
            return existing
        if channel_policy.name and (existing := self.get_channel_policy_by_name(name=channel_policy.name)):
            return existing
        for existing in self.list_channel_policies():
            if existing.matches(channel_policy):
                return existing
        return None

    def delete_channel_policy(self, *, policy_id: UUID) -> KronicleChannelPolicy:
        res = self.delete(route=f"/policies/channels/{policy_id}")
        return KronicleChannelPolicy.from_json(res)

    def patch_channel_policy(self, channel_policy: KronicleChannelPolicy) -> KronicleChannelPolicy:
        res = self.patch(
            route=f"/policies/channels/{channel_policy.id}",
            body=channel_policy.model_dump(),
        )
        return KronicleChannelPolicy.from_json(res)

    # ----------------------------------------------------------------------------------------------
    # Row Policies
    # ----------------------------------------------------------------------------------------------

    def create_row_policy(self, row_policy: KronicleRowPolicy) -> KronicleRowPolicy:
        log_d("create_row_policy", row_policy)
        here = "create_row_policy"
        if existing := self.get_row_policy(row_policy):
            log_i(
                here,
                f"Row policy for {existing.subject.name or existing.subject.type} "
                f"on row {existing.access_profile.row.name} already exists",
            )
            return existing
        res = self.post(route="/policies/rows", body=row_policy.model_dump())
        return KronicleRowPolicy.from_json(res)

    def list_row_policies(self) -> list[KronicleRowPolicy]:
        res = self.get(route="/policies/rows")
        return [KronicleRowPolicy.from_json(r) for r in res] if res else []

    def get_row_policy_by_id(self, *, policy_id: UUID) -> KronicleRowPolicy | None:
        try:
            res = self.get(route=f"/policies/rows/{policy_id}")
        except KronicleHTTPError as e:
            if e.status == 404:
                return None
            raise
        return KronicleRowPolicy.from_json(res) if res else None

    def get_row_policy_by_name(self, *, name: str) -> KronicleRowPolicy | None:
        res = self.get(route=f"/policies/rows?name={name}")
        return KronicleRowPolicy.from_json(res) if res else None

    def get_row_policy(self, row_policy: KronicleRowPolicy) -> KronicleRowPolicy | None:
        if row_policy.id and (existing := self.get_row_policy_by_id(policy_id=row_policy.id)):
            return existing
        if row_policy.name and (existing := self.get_row_policy_by_name(name=row_policy.name)):
            return existing
        for existing in self.list_row_policies():
            if existing.matches(row_policy):
                return existing
        return None

    def delete_row_policy(self, *, policy_id: UUID) -> KronicleRowPolicy:
        res = self.delete(route=f"/policies/rows/{policy_id}")
        return KronicleRowPolicy.from_json(res)

    def patch_row_policy(self, row_policy: KronicleRowPolicy) -> KronicleRowPolicy:
        res = self.patch(route=f"/policies/rows/{row_policy.id}", body=row_policy.model_dump())
        return KronicleRowPolicy.from_json(res)
