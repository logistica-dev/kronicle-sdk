# kronicle_sdk/connectors/rbac/core_setup.py
from uuid import UUID, uuid4

from kronicle_sdk.connectors.abc_connector import KronicleHTTPError
from kronicle_sdk.connectors.auth.kronicle_auth import KronicleUsrLogin
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.rbac.kronicle_zone import KronicleZone
from kronicle_sdk.utils.log import log_i


class KronicleCore(KronicleUsrLogin):
    def __init__(self, url: str, usr: str, pwd: str) -> None:
        super().__init__(url, usr, pwd)

    @property
    def prefix(self) -> str:
        return "/core/v1"

    # ----------------------------------------------------------------------------------------------
    # Zones
    # ----------------------------------------------------------------------------------------------

    def list_zones(self) -> list[KronicleZone]:
        zones = self.get(route="/zones")
        return [KronicleZone.from_json(z) for z in zones]

    def get_zone_by_id(self, zone_id: UUID) -> KronicleZone | None:
        try:
            existing = self.get(route=f"/zones/{zone_id}")
        except KronicleHTTPError as e:
            if e.status == 404:
                return None
            raise
        return KronicleZone.from_json(existing) if existing else None

    def get_zone_by_name(self, name: str) -> KronicleZone | None:
        existing = self.get(route=f"/zones?name={name}")
        return KronicleZone.from_json(existing) if existing else None

    def get_zone(self, zone: KronicleZone) -> KronicleZone | None:
        if zone.id and (existing := self.get_zone_by_id(zone.id)):
            return existing
        if zone.name:
            return self.get_zone_by_name(zone.name)
        return None

    def create_zone(self, zone: KronicleZone) -> KronicleZone:
        here = "create_zone"
        if existing_zone := self.get_zone(zone):
            log_i(here, f"Zone {existing_zone.name} [{existing_zone.id}] already exist")
            return existing_zone
        if zone.id is None:
            zone.id = uuid4()
        created = self.post(route="/zones", body=zone.to_json())
        return KronicleZone.from_json(created)

    def patch_zone(self, zone: KronicleZone) -> KronicleZone:
        body = {}
        if zone.name is not None:
            body["name"] = zone.name
        if zone.details is not None:
            body["details"] = zone.details
        patched = self.patch(route=f"/zones/{zone.id}", body=body)
        return KronicleZone.from_json(patched)

    def delete_zone(self, *, zone_id: UUID) -> KronicleZone | None:
        deleted = self.delete(route=f"/zones/{zone_id}")
        return KronicleZone.from_json(deleted) if deleted else None

    def delete_zone_by_name(self, name: str) -> KronicleZone | None:
        zone = self.get_zone_by_name(name)
        if zone is None:
            return None
        deleted = self.delete(route=f"/zones/{zone.id}")
        return KronicleZone.from_json(deleted) if deleted else None

    # ----------------------------------------------------------------------------------------------
    # Zone Hierarchy
    # ----------------------------------------------------------------------------------------------

    def attach_zone(self, *, parent_id: UUID, child_id: UUID) -> dict:
        """Attach a zone under another one.

        A zone may have at most one parent. The server rejects (HTTP 400) a
        self-attachment, a cycle, and a child that already has a parent.
        """
        return self.post(route=f"/zones/{child_id}/parent", params={"parent_id": str(parent_id)})

    def detach_zone(self, *, parent_id: UUID, child_id: UUID) -> dict:
        """Remove the parent-child link between two zones."""
        return self.delete(route=f"/zones/{child_id}/parent", params={"parent_id": str(parent_id)})

    def list_zone_parents(self, *, zone_id: UUID) -> list[KronicleZone]:
        """List the direct parents of a zone (at most one)."""
        parents = self.get(route=f"/zones/{zone_id}/parents")
        return [KronicleZone.from_json(p) for p in parents]

    def list_zone_children(self, *, zone_id: UUID) -> list[KronicleZone]:
        """List the direct children of a zone."""
        children = self.get(route=f"/zones/{zone_id}/children")
        return [KronicleZone.from_json(c) for c in children]

    def list_zone_ancestors(self, *, zone_id: UUID) -> list[KronicleZone]:
        """List all the ancestors of a zone (transitive)."""
        ancestors = self.get(route=f"/zones/{zone_id}/ancestors")
        return [KronicleZone.from_json(a) for a in ancestors]

    def list_zone_descendants(self, *, zone_id: UUID) -> list[KronicleZone]:
        """List all the descendants of a zone (transitive)."""
        descendants = self.get(route=f"/zones/{zone_id}/descendants")
        return [KronicleZone.from_json(d) for d in descendants]

    def get_zone_parent(self, *, zone_id: UUID) -> KronicleZone | None:
        """Return the parent of a zone, or None when the zone is a root."""
        parents = self.list_zone_parents(zone_id=zone_id)
        return parents[0] if parents else None

    def move_zone_to_parent(self, *, parent_id: UUID, child_id: UUID) -> dict:
        """Move a zone under a new parent, detaching its current parent first."""
        current = self.get_zone_parent(zone_id=child_id)
        if current and current.id is not None and current.id != parent_id:
            self.detach_zone(parent_id=current.id, child_id=child_id)
        return self.attach_zone(parent_id=parent_id, child_id=child_id)

    # ----------------------------------------------------------------------------------------------
    # Core Channels
    # ----------------------------------------------------------------------------------------------

    def list_core_channels(self, *, zone_id: UUID | None = None) -> list[KronicleChannel]:
        if zone_id:
            channels = self.get(route=f"/zones/{zone_id}/channels")
        else:
            channels = self.get(route="/channels")
        return [KronicleChannel.from_json(c) for c in channels]

    def get_core_channel(self, *, channel_id: UUID) -> KronicleChannel | None:
        existing = self.get(route=f"/channels/{channel_id}")
        return KronicleChannel.from_json(existing) if existing else None

    def patch_core_channel(
        self,
        *,
        channel_id: UUID,
        name: str | None = None,
        details: dict | None = None,
        zone_id: UUID | None = None,
    ) -> KronicleChannel:
        body = {}
        if name is not None:
            body["name"] = name
        if details is not None:
            body["details"] = details
        if zone_id is not None:
            body["zone_id"] = str(zone_id)
        return KronicleChannel.from_json(self.patch(route=f"/channels/{channel_id}", body=body))

    def change_channel_zone(self, *, channel_id: UUID, zone_id: UUID) -> KronicleChannel:
        """Move an existing channel to another zone.

        Explicit convenience wrapper over :meth:`patch_core_channel` for the
        zone-only case.
        """
        return self.patch_core_channel(channel_id=channel_id, zone_id=zone_id)

    def delete_core_channel(self, channel_id: UUID) -> KronicleChannel:
        return KronicleChannel.from_json(self.delete(route=f"/channels/{channel_id}"))

    # ----------------------------------------------------------------------------------------------
    # Sync
    # ----------------------------------------------------------------------------------------------

    def sync_core_channels(self) -> dict:
        return self.post(route="/sync")
