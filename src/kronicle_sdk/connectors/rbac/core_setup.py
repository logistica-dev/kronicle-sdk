# kronicle_sdk/connectors/rbac/core_setup.py
from uuid import UUID

from kronicle_sdk.connectors.auth.kronicle_auth import KronicleUsrLogin
from kronicle_sdk.models.rbac.kronicle_zone import KronicleZone


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

    def get_zone_by_id(self, *, zone_id: UUID) -> KronicleZone | None:
        res = self.get(route=f"/zones/{zone_id}")
        return KronicleZone.from_json(res) if res else None

    def create_zone(self, zone: KronicleZone) -> KronicleZone:
        res = self.post(route="/zones", body=zone.to_json())
        return KronicleZone.from_json(res)

    def patch_zone(self, zone: KronicleZone) -> KronicleZone:
        body = {}
        if zone.name is not None:
            body["name"] = zone.name
        if zone.details is not None:
            body["details"] = zone.details
        res = self.patch(route=f"/zones/{zone.id}", body=body)
        return KronicleZone.from_json(res)

    def delete_zone(self, *, zone_id: UUID) -> KronicleZone | None:
        res = self.delete(route=f"/zones/{zone_id}")
        return KronicleZone.from_json(res) if res else None

    # ----------------------------------------------------------------------------------------------
    # Core Channels
    # ----------------------------------------------------------------------------------------------

    def list_core_channels(self, *, zone_id: UUID | None = None) -> list[dict]:
        if zone_id:
            channels = self.get(route=f"/zones/{zone_id}/channels")
        channels = self.get(route="/channels")
        return channels

    def get_core_channel(self, *, channel_id: UUID) -> dict | None:
        res = self.get(route=f"/channels/{channel_id}")
        return res if res else None

    def patch_core_channel(
        self,
        *,
        channel_id: UUID,
        name: str | None = None,
        details: dict | None = None,
        zone_id: UUID | None = None,
    ) -> dict:
        body = {}
        if name is not None:
            body["name"] = name
        if details is not None:
            body["details"] = details
        if zone_id is not None:
            body["zone_id"] = str(zone_id)
        return self.patch(route=f"/channels/{channel_id}", body=body)

    def delete_core_channel(self, channel_id: UUID):
        return self.delete(route=f"/channels/{channel_id}")

    # ----------------------------------------------------------------------------------------------
    # Sync
    # ----------------------------------------------------------------------------------------------

    def sync_core_channels(self) -> dict:
        return self.post(route="/sync")
