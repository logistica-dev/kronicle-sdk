# connectors/kronicle_writer.py
from typing import Any

from kronicle.connectors.abc_connector import KronicleAbstractConnector
from kronicle.models.iso_datetime import IsoDateTime
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

    def insert_rows_and_upsert_channel(self, body: KroniclePayload | dict):
        """Creates a new channel if it doesn't exist already and insert data rows"""
        payload = self._ensure_body_as_payload(body)
        return self.post(route="channels", body=payload)

    def add_row(self, body: KroniclePayload | dict):
        """Creates a new channel if it doesn't exist already and insert data rows"""
        payload = self._ensure_body_as_payload(body)
        return self.insert_rows_and_upsert_channel(body=payload)

    def insert_rows(self, id, rows: list[dict[str, Any]]):
        """Insert rows for an existing channel"""
        payload = KroniclePayload(channel_id=id, rows=rows)
        return self.post(f"channels/{id}/rows", body=payload)


if __name__ == "__main__":

    from kronicle.models.iso_datetime import now_local
    from kronicle.utils.log import log_d
    from kronicle.utils.str_utils import tiny_id, uuid4_str

    here = "KronicleWriter"
    log_d(here)
    kronicle_writer = KronicleWriter("http://127.0.0.1:8000")
    [log_d(here, f"Channel {channel.channel_id}", channel) for channel in kronicle_writer.all_channels]
    max_chan_id, _ = kronicle_writer.get_channel_with_max_rows()
    if max_chan_id:
        log_d(here, "channel with max rows", kronicle_writer.get_channel(max_chan_id))
        rows: list = kronicle_writer.get_rows_for_channel(max_chan_id, "dict")  # type:ignore
        for i, row in enumerate(rows):
            log_d(here, f"row {i}", row)
        log_d(here, "nb rows", len(rows))

    channel_id = uuid4_str()
    channel_name = f"demo_channel_{tiny_id()}"
    now_tag = now_local()

    payload = {
        "channel_id": channel_id,
        "channel_name": channel_name,
        "channel_schema": {"time": IsoDateTime, "temperature": float},
        "metadata": {"unit": "°C"},
        "tags": {"test": now_tag},
        "rows": [
            {"time": "2025-01-01T00:00:00Z", "temperature": 12.3},
            {"time": "2025-01-01T00:01:00Z", "temperature": 12.8},
        ],
    }
    log_d(here, "payload", payload)
    result = kronicle_writer.insert_rows_and_upsert_channel(payload)
    log_d(here, "result", result)
