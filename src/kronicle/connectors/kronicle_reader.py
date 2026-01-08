# connectors/kronicle_reader.py


from kronicle.connectors.abc_connector import KronicleAbstractConnector


class KronicleReader(KronicleAbstractConnector):
    """
    Reads channels on a Kronicle microservice
    """

    def __init__(self, url: str = "http://127.0.0.1:8000"):
        super().__init__(url)

    @property
    def prefix(self) -> str:
        return "api/v1"


if __name__ == "__main__":
    from kronicle.utils.log import log_d

    here = "read Kronicle"
    log_d(here)
    kronicle_reader = KronicleReader("http://127.0.0.1:8000")
    log_d(here, "is_alive", kronicle_reader.is_alive())
    log_d(here, "is_ready", kronicle_reader.is_ready())
    log_d(here, "nb channels", len(kronicle_reader.all_channels))
    chan_id, _ = kronicle_reader.get_channel_with_max_rows()
    if chan_id:
        log_d(here, "channel with max rows", kronicle_reader.get_channel(chan_id))

    # try:
    #     id = uuid4()
    #     log_d(here, "random channel", kronicle_reader.get_channel(id))
    # except KronicleHTTPError as e:
    #     log_w(here, f"Channel {id}", e)
