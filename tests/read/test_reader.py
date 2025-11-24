# tests/test_kronicle_reader.py
from unittest.mock import patch

import pytest
from pandas import DataFrame

from connectors.abc_connector import KroniclePayload
from connectors.kronicle_reader import KronicleReader
from models.iso_datetime import now_utc
from utils.str_utils import tiny_id, uuid4_str

sensor_id = uuid4_str()
sensor_name = f"channel_{tiny_id()}"
payload_example = {
    "sensor_id": sensor_id,
    "sensor_name": sensor_name,
    "sensor_schema": {"time": "datetime", "temperature": "float"},
    "metadata": {"unit": "C"},
    "tags": {"test": True},
    "rows": [
        {"time": now_utc(), "temperature": 21.5},
        {"time": now_utc(), "temperature": 22.3},
    ],
    "columns": {"time": [now_utc(), now_utc()], "temperature": [21.5, 22.3]},
    "received_at": now_utc(),
    "available_data": 2,
    "op_status": "success",
    "op_details": {"issued_at": now_utc()},
}


@pytest.fixture
def mock_payload():
    return KroniclePayload(**payload_example)


@pytest.fixture
def reader():
    return KronicleReader("http://fake-url")


# -------------------------------
# Mocking _request to avoid HTTP
# -------------------------------


@pytest.fixture
def patch_request(mock_payload):
    with patch.object(KronicleReader, "_request", return_value=[mock_payload]) as mock:
        yield mock


# -------------------------------
# Tests
# -------------------------------


def test_get_all_channels(reader, patch_request, mock_payload):
    channels = reader.all_channels
    assert isinstance(channels, list)
    assert all(isinstance(ch, KroniclePayload) for ch in channels)
    assert channels[0].sensor_id == mock_payload.sensor_id


def test_all_channels_caching(reader, patch_request, mock_payload):
    # Should call _request once for cache
    channels1 = reader.all_channels
    channels2 = reader.all_channels
    patch_request.assert_called_once()
    assert channels1 == channels2


def test_all_ids(reader, patch_request, mock_payload):
    assert reader.all_ids == [mock_payload.sensor_id]


def test_get_channel_existing(reader, patch_request, mock_payload):
    channel_id = mock_payload.sensor_id
    # patch _request to return single payload for channel
    patch_request.return_value = mock_payload
    result = reader.get_channel(channel_id)
    assert isinstance(result, KroniclePayload)
    assert result.sensor_id == channel_id


def test_get_channel_nonexistent(reader, patch_request):
    patch_request.return_value = None
    assert reader.get_channel(uuid4_str()) is None


def test_get_channel_by_sensor_name_found(reader, patch_request, mock_payload):
    patch_request.return_value = [mock_payload]
    result = reader.get_channel_by_sensor_name(sensor_name)
    assert result.sensor_name == sensor_name


def test_get_channel_by_sensor_name_not_found(reader, patch_request, mock_payload):
    patch_request.return_value = [mock_payload]
    result = reader.get_channel_by_sensor_name("missing_sensor")
    assert result is None


def test_get_channel_with_max_rows(reader, patch_request, mock_payload):
    patch_request.return_value = [mock_payload]
    channel_id, max_rows = reader.get_channel_with_max_rows()
    # assert max_rows and max_rows > 0


@pytest.mark.parametrize("return_type", ["list", "dict", "df", "str"])
def test_get_rows_for_channel(reader, patch_request, mock_payload, return_type):
    patch_request.return_value = mock_payload
    res = reader.get_rows_for_channel(mock_payload.sensor_id, return_type=return_type)
    if return_type == "df":
        assert isinstance(res, DataFrame)
    elif return_type == "str":
        assert isinstance(res, str)
    else:
        assert isinstance(res, list)
        assert res == mock_payload.rows


@pytest.mark.parametrize("return_type", ["list", "dict", "df", "str"])
def test_get_cols_for_channel(reader, patch_request, mock_payload, return_type):
    patch_request.return_value = mock_payload
    res = reader.get_cols_for_channel(mock_payload.sensor_id, return_type=return_type)
    if return_type == "df":
        assert isinstance(res, DataFrame)
    elif return_type == "str":
        assert isinstance(res, str)
    else:
        assert isinstance(res, dict) or isinstance(res, list)
