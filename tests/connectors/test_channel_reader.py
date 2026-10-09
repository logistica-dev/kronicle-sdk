# tests/connectors/test_channel_reader.py
from kronicle_sdk.connectors.channel.channel_reader import KronicleReader


class TestKronicleReader:
    def test_prefix(self):
        reader = KronicleReader(url="http://localhost:8765", usr="admin", pwd="secret")
        assert reader.prefix == "/api/v1"
