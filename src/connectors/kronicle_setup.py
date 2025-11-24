from uuid import UUID

from connectors.kronicle_writer import KronicleWriter
from models.kronicle_errors import KronicleOperationError
from models.kronicle_payload import KroniclePayload
from utils.log import log_w


class KronicleSetup(KronicleWriter):
    def __init__(self, url):
        super().__init__(url)

    @property
    def prefix(self) -> str:
        return "setup/v1"

    def create_channel(self, body: KroniclePayload | dict):
        self._ensure_payload_id(body)
        return self.post(route="channels", body=body)

    def upsert_channel(self, body: KroniclePayload | dict):
        self._ensure_payload_id(body)
        return self.put(route="channels", body=body)

    def update_channel(self, body: KroniclePayload | dict):
        sensor_id = self._ensure_payload_id(body)
        return self.patch(route=f"channels/{sensor_id}", body=body)

    def delete_channel(self, id: UUID | str):
        channel: KroniclePayload | None = self.get_channel(id)
        if not channel:
            raise KronicleOperationError(f"No sensor found with id {id} on {self.url}")
        return self.delete(route=f"channels/{channel.sensor_id}")

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
    from utils.log import log_d

    here = "read Kronicle"
    log_d(here)
    kronicle_setup = KronicleSetup("http://127.0.0.1:8000")
    [log_d(here, f"channel {channel.sensor_id}", channel) for channel in kronicle_setup.all_channels]
    log_d(here, "column types", kronicle_setup.column_types)
    chan_id, _ = kronicle_setup.get_channel_with_max_rows()
    if chan_id:
        log_d(here, "channel with max rows", chan_id)
