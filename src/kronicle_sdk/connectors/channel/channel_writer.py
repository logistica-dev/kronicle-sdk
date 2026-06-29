# kronicle/connectors/channel/kronicle_writer.py
from typing import Any
from uuid import UUID

from kronicle_sdk.conf.read_conf import Settings
from kronicle_sdk.connectors.channel.abc_channel_connector import (
    KronicleAbstractChannelConnector,
)
from kronicle_sdk.models.data.kronicle_payload import KroniclePayload
from kronicle_sdk.models.iso_datetime import IsoDateTime, now_local
from kronicle_sdk.utils.str_utils import ensure_uuid4, tiny_id, uuid4_str


class KronicleWriter(KronicleAbstractChannelConnector):
    """
    SDK to push and read data on a Kronicle
    """

    #
    def __init__(self, url: str, usr: str, pwd: str):
        super().__init__(url, usr, pwd)

    @property
    def prefix(self) -> str:
        return "/data/v1"

    def create_channel(self, body: KroniclePayload | dict, *, zone_id: UUID | str):
        """Creates a new channel if it doesn't exist already and insert data rows"""
        zone_id = ensure_uuid4(zone_id)
        payload = self._ensure_body_as_payload(body)
        return self.post(route=f"zones/{zone_id}/channels", body=payload)

    def patch_channel(
        self,
        body: KroniclePayload | dict,
        *,
        zone_id: UUID | str | None = None,
    ):
        """Creates a new channel if it doesn't exist already and insert data rows"""
        zone_id = ensure_uuid4(zone_id) if zone_id else None
        payload = self._ensure_body_as_payload(body)
        channel_id = ensure_uuid4(payload.channel_id)
        return self.patch(route=f"channels/{channel_id}", body=payload)

    def insert_rows_and_update_channel(self, body: KroniclePayload | dict):
        """Creates a new channel if it doesn't exist already and insert data rows"""
        payload = self._ensure_body_as_payload(body)
        channel_id = ensure_uuid4(payload.channel_id)
        return self.post(route=f"channels/{channel_id}", body=payload)

    # def add_rows(self, body: KroniclePayload | dict):
    #     """Creates a new channel if it doesn't exist already and insert data rows"""
    #     payload = self._ensure_body_as_payload(body)
    #     return self.insert_rows_and_upsert_channel(body=payload)

    def insert_rows(self, id, rows: list[dict[str, Any]]):
        """Insert rows for an existing channel"""
        payload = KroniclePayload(channel_id=id, rows=rows)
        return self.post(f"channels/{id}/rows", body=payload)


if __name__ == "__main__":  # pragma: no-cover
    from kronicle_sdk.utils.log import log_d

    here = "KronicleWriter"
    log_d(here)
    co = Settings().connection
    log_d(here, "Connecting to", co.url)
    kronicle_writer = KronicleWriter.from_connection_info(co)
    [log_d(here, f"Channel {channel.channel_id}", channel) for channel in kronicle_writer.all_channels]
    max_chan = kronicle_writer.get_channel_with_max_rows()
    if max_chan and (max_chan_id := max_chan.channel_id):
        log_d(here, "channel with max rows", kronicle_writer.get_channel(max_chan_id))
        rows = kronicle_writer.get_rows_for_channel(max_chan_id)
        assert isinstance(rows, list)
        for i, row in enumerate(rows):
            log_d(here, f"row {i}", row)
        log_d(here, "nb rows", len(rows))

        cols = kronicle_writer.get_cols_for_channel(max_chan_id)
        assert isinstance(cols, dict)
        log_d(here, "cols", cols)

    channel_id = uuid4_str()
    channel_name = f"demo_channel_{tiny_id()}"
    now_tag = now_local()

    payload = {
        "channel_id": channel_id,
        "name": channel_name,
        "channel_schema": {"time": IsoDateTime, "temperature": float},
        "metadata": {"unit": "°C"},
        "tags": {"test": now_tag},
        "rows": [
            {"time": now_tag, "temperature": 12.3},
            {"time": now_tag, "temperature": 12.8},
        ],
    }
    log_d(here, "payload", payload)
    result = kronicle_writer.insert_rows_and_update_channel(payload)
    log_d(here, "result", result)
    # log_d(here, "channels", kronicle_writer.get_all_channels(should_log=True))
    # log_d(
    #     here,
    #     "channels",
    #     kronicle_writer.get(route="channels"),
    # )

    id = "592bc15e-9aa4-44d0-b18e-9b168572690c"
    payload = kronicle_writer._ensure_is_payload_or_none(
        kronicle_writer.get(
            route=f"channels/{id}/rows?min[time]=2026-03-31T12:04:14.476554Z&max[time]=2026-03-31T12:04:14.476554Z"
        )
    )
    log_d(here, "payload", payload)
