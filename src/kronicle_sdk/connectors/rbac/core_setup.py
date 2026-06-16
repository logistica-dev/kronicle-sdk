# kronicle_sdk/connectors/rbac/rbac_resource_setup.py
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

    def create_zone(self, zone: KronicleZone) -> KronicleZone:
        res = self.post(route="/zones", body=zone.to_json())
        return KronicleZone(**res)

    def get_zones(self) -> list[KronicleZone]:
        zones = self.get(route="/zones")
        return [KronicleZone(**z) for z in zones]

    def get_zone(self, zone_id: UUID | str) -> KronicleZone | None:
        res = self.get(route=f"/zones/{zone_id}")
        return KronicleZone(**res) if res else None

    def patch_zone(self, zone_id: UUID | str, name: str | None = None, details: dict | None = None) -> KronicleZone:
        body = {}
        if name is not None:
            body["name"] = name
        if details is not None:
            body["details"] = details
        res = self.patch(route=f"/zones/{zone_id}", body=body)
        return KronicleZone(**res)

    def delete_zone(self, zone_id: UUID | str) -> KronicleZone | None:
        res = self.delete(route=f"/zones/{zone_id}")
        return KronicleZone(**res) if res else None

    # ----------------------------------------------------------------------------------------------
    # Core Channels
    # ----------------------------------------------------------------------------------------------

    def get_core_channels(self, zone_id: UUID | str | None = None) -> list[dict]:
        if zone_id:
            return self.get(route=f"/zones/{zone_id}/channels")
        return self.get(route="/channels")

    def get_core_channel(self, channel_id: UUID | str) -> dict | None:
        res = self.get(route=f"/channels/{channel_id}")
        return res if res else None

    def patch_core_channel(
        self,
        channel_id: UUID | str,
        name: str | None = None,
        details: dict | None = None,
        zone_id: UUID | str | None = None,
    ) -> dict:
        body = {}
        if name is not None:
            body["name"] = name
        if details is not None:
            body["details"] = details
        if zone_id is not None:
            body["zone_id"] = str(zone_id)
        return self.patch(route=f"/channels/{channel_id}", body=body)

    # ----------------------------------------------------------------------------------------------
    # Sync
    # ----------------------------------------------------------------------------------------------

    def sync_core_channels(self) -> dict:
        return self.post(route="/sync")
