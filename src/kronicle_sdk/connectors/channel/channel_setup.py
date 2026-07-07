# kronicle/connectors/channel/kronicle_setup.py
from uuid import UUID, uuid4

from kronicle_sdk.conf.read_conf import Settings
from kronicle_sdk.connectors.channel.channel_writer import KronicleWriter
from kronicle_sdk.connectors.rbac.core_setup import KronicleCore
from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.iso_datetime import now_local
from kronicle_sdk.models.kronicle_errors import KronicleOperationError
from kronicle_sdk.models.rbac.kronicle_zone import KronicleZone
from kronicle_sdk.utils.log import log_w
from kronicle_sdk.utils.str_utils import ensure_uuid4, tiny_id, uuid4_str


class KronicleSetup(KronicleWriter):
    def __init__(self, url: str, usr: str, pwd: str):
        super().__init__(url, usr, pwd)

    @property
    def prefix(self) -> str:
        return "/setup/v1"

    @property
    def column_types(self):
        return self.get(route="schemas/column_types", strict=False)

    def create_channel(self, body: KronicleChannel | dict, *, zone_id: UUID | str):
        """Creates a new channel in a zone and inserts data rows."""
        zone_id = ensure_uuid4(zone_id)
        payload = self._ensure_body_as_payload(body)
        return self.post(route=f"zones/{zone_id}/channels", body=payload)

    def upsert_channel(self, body: KronicleChannel | dict):
        self._ensure_payload_id(body)
        return self.put(route="channels", body=body)

    def update_channel(self, body: KronicleChannel | dict):
        channel_id = self._ensure_payload_id(body)
        return self.patch(route=f"channels/{channel_id}", body=body)

    def delete_channel(self, id: UUID | str):
        channel: KronicleChannel | None = self.get_channel(id)
        if not channel:
            raise KronicleOperationError(f"No channel found with id {id} on {self.url}")
        return self.delete(route=f"channels/{channel.id}")

    def delete_all_channels(self):
        here = "delete_all_channels"
        for channel_id in self.all_ids:
            try:
                self.delete_channel(channel_id)
                print(f"deleted channel {channel_id}")
            except Exception as e:
                log_w(here, f"Could not delete channel {channel_id}", e)

    def clone_channel(self, src_id: UUID | str, *, body: KronicleChannel | dict | None = None):
        if isinstance(src_id, str):
            src_id = UUID(src_id)
        if not body:
            body = KronicleChannel(id=src_id)
        elif isinstance(body, KronicleChannel):
            body.id = src_id
        else:
            body = KronicleChannel(id=src_id, **body)
        return self.post(route=f"channels/{src_id}/clone", body=body)


if __name__ == "__main__":  # pragma: no-cover
    from kronicle_sdk.utils.log import log_d

    here = "ksetup"
    log_d(here)
    co = Settings().connection
    kronicle_setup = KronicleSetup.from_connection_info(co)
    log_d(here, "Channel list vvv")
    [log_d(here, f"channel {channel.id}", channel) for channel in kronicle_setup.all_channels]
    log_d(here, "Channel list ^^^")

    max_chan = kronicle_setup.get_channel_with_max_rows()
    if max_chan and (max_chan_id := max_chan.id):
        log_d(here, "channel with max rows", kronicle_setup.get_channel(max_chan_id))
        rows: list = kronicle_setup.get_rows_for_channel(max_chan_id, "dict")  # type:ignore
        for i, row in enumerate(rows):
            log_d(here, f"row {i}", row)
        log_d(here, "nb rows", len(rows))

    channel_id = uuid4_str()
    channel_name = f"demo_channel_{tiny_id()}"

    now_tag = now_local()

    payload = KronicleChannel.from_json(
        {
            "id": channel_id,
            "name": channel_name,
            "channel_schema": {"time": "datetime", "temperature": "float"},
            "metadata": {"unit": "°C"},
            "tags": {"test": now_tag},
            "rows": [
                {"time": "2025-01-10T00:00:00Z", "temperature": 12.3},
                {"time": "2025-01-10T00:01:00Z", "temperature": 12.8},
            ],
        }
    )
    log_d(here, "payload", payload)
    core_setup = KronicleCore.from_connection_info(co)
    zone_id = uuid4()
    zone = KronicleZone(id=zone_id, name="test_channel_setup_zone", details={"test": True})
    core_setup.create_zone(zone)
    result = kronicle_setup.create_channel(payload, zone_id=zone_id)
    log_d(here, "result", result)
    log_d(here, "column types", kronicle_setup.column_types)
    try:
        kronicle_setup.get(route="route/that/does/not/exist", strict=False)
    except Exception as e:
        log_w(here, "OK, exception caught:", e)

    core_setup.delete_zone(zone_id=zone_id)
