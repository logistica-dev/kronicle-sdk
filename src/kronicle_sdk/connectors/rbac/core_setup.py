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
