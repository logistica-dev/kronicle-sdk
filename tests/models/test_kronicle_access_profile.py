# tests/models/test_kronicle_access_profile.py
from uuid import uuid4

from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.rbac.kronicle_access_profile import (
    KronicleAccessProfile,
    KronicleChannelAccess,
    KronicleRowAccess,
    KronicleZoneAccess,
)
from kronicle_sdk.models.rbac.kronicle_role import KronicleRole
from kronicle_sdk.models.rbac.kronicle_row import KronicleRow
from kronicle_sdk.models.rbac.kronicle_zone import KronicleZone


def _role() -> KronicleRole:
    return KronicleRole(id=uuid4(), name="writer", permissions=["channel:read"])


def _zone() -> KronicleZone:
    return KronicleZone(id=uuid4(), name="ZoneA")


def _channel() -> KronicleChannel:
    return KronicleChannel(id=uuid4(), name="chan")


def _row() -> KronicleRow:
    return KronicleRow(id=1, channel_id=uuid4())


class TestKronicleAccessProfile:
    def test_model_dump_without_flatten(self):
        d = KronicleAccessProfile(role=_role()).model_dump()
        assert "role" in d
        assert "role_id" not in d

    def test_model_dump_flatten(self):
        role = _role()
        d = KronicleAccessProfile(role=role).model_dump(flatten=True)
        assert role.id
        assert d["role_id"] == role.id.hex
        assert d["role_name"] == "writer"
        assert "role" not in d

    def test_from_json(self):
        ap = KronicleAccessProfile.from_json({"name": "access.profile", "role": {"name": "writer"}})
        assert ap.name == "access.profile"
        assert ap.role.name == "writer"


class TestKronicleZoneAccess:
    def test_model_dump_without_flatten(self):
        d = KronicleZoneAccess(role=_role(), zone=_zone()).model_dump()
        assert "zone" in d
        assert "zone_id" not in d

    def test_model_dump_flatten(self):
        zone = _zone()
        d = KronicleZoneAccess(role=_role(), zone=zone).model_dump(flatten=True)
        assert zone.id
        assert d["zone_id"] == zone.id.hex
        assert d["zone_name"] == "ZoneA"
        assert "zone" not in d

    def test_from_json(self):
        za = KronicleZoneAccess.from_json({"role": {"name": "writer"}, "zone": {"name": "ZoneA"}})
        assert za.role.name == "writer"
        assert za.zone.name == "ZoneA"


class TestKronicleChannelAccess:
    def test_model_dump_without_flatten(self):
        d = KronicleChannelAccess(role=_role(), channel=_channel()).model_dump()
        assert "channel" in d
        assert "channel_name" not in d

    def test_model_dump_flatten(self):
        channel = _channel()
        d = KronicleChannelAccess(role=_role(), channel=channel).model_dump(flatten=True)
        assert channel.id
        assert d["id"] == channel.id.hex
        assert d["channel_name"] == "chan"
        assert "channel" not in d

    def test_from_json(self):
        ca = KronicleChannelAccess.from_json({"role": {"name": "writer"}, "channel": {"name": "chan"}})
        assert ca.role.name == "writer"
        assert ca.channel.name == "chan"


class TestKronicleRowAccess:
    def test_from_json(self):
        ra = KronicleRowAccess.from_json(
            {
                "role": {"name": "writer"},
                "row": {"id": 2, "channel_id": str(uuid4()), "name": "test.row"},
            }
        )
        assert ra.role.name == "writer"
        assert ra.row.id == 2
