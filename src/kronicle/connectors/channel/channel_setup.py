# kronicle/connectors/channel/kronicle_setup.py
from uuid import UUID

from kronicle.conf.read_conf import Settings
from kronicle.connectors.channel.channel_writer import KronicleWriter
from kronicle.models.data.kronicle_payload import KroniclePayload
from kronicle.models.iso_datetime import now_local
from kronicle.models.kronicle_errors import KronicleOperationError
from kronicle.utils.log import log_w
from kronicle.utils.str_utils import tiny_id, uuid4_str


class KronicleSetup(KronicleWriter):
    def __init__(self, url: str, usr: str, pwd: str):
        super().__init__(url, usr, pwd)

    @property
    def prefix(self) -> str:
        return "/setup/v1"

    @property
    def column_types(self):
        return self.get(route="schemas/column_types", strict=False)

    def create_channel(self, body: KroniclePayload | dict):
        self._ensure_payload_id(body)
        return self.post(route="channels", body=body)

    def upsert_channel(self, body: KroniclePayload | dict):
        self._ensure_payload_id(body)
        return self.put(route="channels", body=body)

    def update_channel(self, body: KroniclePayload | dict):
        channel_id = self._ensure_payload_id(body)
        return self.patch(route=f"channels/{channel_id}", body=body)

    def delete_channel(self, id: UUID | str):
        channel: KroniclePayload | None = self.get_channel(id)
        if not channel:
            raise KronicleOperationError(f"No channel found with id {id} on {self.url}")
        return self.delete(route=f"channels/{channel.channel_id}")

    def delete_all_channels(self):
        here = "delete_all_channels"
        for channel_id in self.all_ids:
            try:
                self.delete_channel(channel_id)
                print(f"deleted channel {channel_id}")
            except Exception as e:
                log_w(here, f"Could not delete channel {channel_id}", e)

    def clone_channel(self, id: UUID | str, body: KroniclePayload | dict | None):
        if not body:
            self.post(route=f"channels/{id}/clone")
        self.post(route=f"channels/{id}/clone", body=body)


if __name__ == "__main__":
    from kronicle.utils.log import log_d

    here = "ksetup"
    log_d(here)
    co = Settings().connection
    kronicle_setup = KronicleSetup(co.url, co.usr, co.pwd)
    log_d(here, "Channel list vvv")
    [log_d(here, f"channel {channel.channel_id}", channel) for channel in kronicle_setup.all_channels]
    log_d(here, "Channel list ^^^")

    max_chan_id, _ = kronicle_setup.get_channel_with_max_rows()
    if max_chan_id:
        log_d(here, "channel with max rows", kronicle_setup.get_channel(max_chan_id))
        rows: list = kronicle_setup.get_rows_for_channel(max_chan_id, "dict")  # type:ignore
        for i, row in enumerate(rows):
            log_d(here, f"row {i}", row)
        log_d(here, "nb rows", len(rows))

    channel_id = uuid4_str()
    channel_name = f"demo_channel_{tiny_id()}"

    now_tag = now_local()

    payload = {
        "channel_id": channel_id,
        "channel_name": channel_name,
        "channel_schema": {"time": "datetime", "temperature": "float"},
        "metadata": {"unit": "°C"},
        "tags": {"test": now_tag},
        "rows": [
            {"time": "2025-01-10T00:00:00Z", "temperature": 12.3},
            {"time": "2025-01-10T00:01:00Z", "temperature": 12.8},
        ],
    }
    log_d(here, "payload", payload)
    result = kronicle_setup.insert_rows_and_upsert_channel(payload)
    log_d(here, "result", result)
    log_d(here, "column types", kronicle_setup.column_types)
    try:
        kronicle_setup.get(route="route/that/does/not/exist", strict=False)
    except Exception as e:
        log_w(here, "OK, exception caught:", e)
