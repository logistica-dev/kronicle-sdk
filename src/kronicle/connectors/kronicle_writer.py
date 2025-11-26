# connectors/kronicle_writer.py
from typing import Any

from kronicle.connectors.abc_connector import KronicleAbstractConnector
from kronicle.models.kronicle_payload import KroniclePayload


class KronicleWriter(KronicleAbstractConnector):
    """
    SDK to push and read data on a Kronicle
    """

    def __init__(self, url):
        super().__init__(url)

    @property
    def prefix(self) -> str:
        return "data/v1"

    @property
    def column_types(self):
        return self.get(route="schemas/columns/types", strict=False)

    def insert_rows_and_upsert_channel(self, body: KroniclePayload | dict):
        """Creates a new channel if it doesn't exist already and insert data rows"""
        self._ensure_payload_id(body)
        return self.post(route="channels", body=body)

    def add_row(self, body: KroniclePayload | dict):
        """Creates a new channel if it doesn't exist already and insert data rows"""
        return self.insert_rows_and_upsert_channel(body)

    def insert_rows(self, id, rows: list[dict[str, Any]]):
        """Insert rows for an existing sensor"""
        payload = KroniclePayload(sensor_id=id, rows=rows)
        return self.post(f"channels/{id}/rows", body=payload.model_dump())


if __name__ == "__main__":
    from kronicle.utils.log import log_d

    here = "read Kronicle"
    log_d(here)
    kronicle_writer = KronicleWriter("http://127.0.0.1:8000")
    [log_d(here, f"Channel {channel.sensor_id}", channel) for channel in kronicle_writer.all_channels]
    max_chan_id, _ = kronicle_writer.get_channel_with_max_rows()
    if max_chan_id:
        log_d(here, "channel with max rows", kronicle_writer.get_channel(max_chan_id))
        rows: list = kronicle_writer.get_rows_for_channel(max_chan_id, "dict")  # type:ignore
        for i, row in enumerate(rows):
            log_d(here, f"row {i}", row)
        log_d(here, "nb rows", len(rows))
