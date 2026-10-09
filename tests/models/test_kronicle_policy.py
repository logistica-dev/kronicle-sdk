# tests/models/test_kronicle_policy.py
from uuid import uuid4

from kronicle_sdk.models.data.kronicle_channel import KronicleChannel
from kronicle_sdk.models.rbac.kronicle_access_profile import (
    KronicleChannelAccess,
    KronicleRowAccess,
    KronicleZoneAccess,
)
from kronicle_sdk.models.rbac.kronicle_group import KronicleGroup
from kronicle_sdk.models.rbac.kronicle_policy import (
    KronicleChannelPolicy,
    KronicleRowPolicy,
    KronicleSubject,
    KronicleZonePolicy,
)
from kronicle_sdk.models.rbac.kronicle_role import KronicleRole
from kronicle_sdk.models.rbac.kronicle_row import KronicleRow
from kronicle_sdk.models.rbac.kronicle_user import KronicleUser
from kronicle_sdk.models.rbac.kronicle_zone import KronicleZone


def _role(name: str = "writer") -> KronicleRole:
    return KronicleRole(id=uuid4(), name=name, permissions=["channel:read"])


def _zone(name: str = "ZoneA") -> KronicleZone:
    return KronicleZone(id=uuid4(), name=name)


def _channel(name: str = "chan") -> KronicleChannel:
    return KronicleChannel(id=uuid4(), name=name)


def _row(row_id: int = 1) -> KronicleRow:
    return KronicleRow(id=row_id, channel_id=uuid4())


def _user_subject() -> KronicleSubject:
    return KronicleSubject(name="subj", type="user", user_id=uuid4())


class TestKronicleSubject:
    def test_from_user(self):
        uid = uuid4()
        user = KronicleUser(id=uid, name="test.user", email="user@example.com")
        subject = KronicleSubject.from_user(user)
        assert subject.type == "user"
        assert subject.user_id == uid
        assert subject.name == user.name

    def test_from_group(self):
        gid = uuid4()
        group = KronicleGroup(id=gid, name="Admins")
        subject = KronicleSubject.from_group(group)
        assert subject.type == "group"
        assert subject.group_id == gid
        assert subject.name == group.name

    def test_defaults(self):
        subject = KronicleSubject(type="group")
        assert subject.user_id is None
        assert subject.group_id is None


class TestKronicleZonePolicy:
    def test_from_json(self):
        zp = KronicleZonePolicy.from_json(
            {
                "id": str(uuid4()),
                "name": "zone-policy",
                "details": {"a": 1},
                "description": "desc",
                "is_delegation": True,
                "delegation_start": "2026-01-01T00:00:00+00:00",
                "delegation_end": "2026-02-01T00:00:00+00:00",
                "subject": {"type": "user", "name": "subj", "user_id": str(uuid4())},
                "access_profile": {"role": {"name": "writer"}, "zone": {"name": "ZoneA"}},
            }
        )
        assert zp.name == "zone-policy"
        assert zp.is_delegation is True
        assert zp.access_profile.zone.name == "ZoneA"

    def test_matches_true(self):
        subject = _user_subject()
        zone = _zone()
        role = _role()
        p1 = KronicleZonePolicy(subject=subject, access_profile=KronicleZoneAccess(role=role, zone=zone))
        p2 = KronicleZonePolicy(subject=subject, access_profile=KronicleZoneAccess(role=role, zone=zone))
        assert p1.matches(p2) is True

    def test_matches_false_on_subject(self):
        zone, role = _zone(), _role()
        p1 = KronicleZonePolicy(subject=_user_subject(), access_profile=KronicleZoneAccess(role=role, zone=zone))
        p2 = KronicleZonePolicy(subject=_user_subject(), access_profile=KronicleZoneAccess(role=role, zone=zone))
        assert p1.matches(p2) is False

    def test_matches_false_on_role(self):
        subject, zone = _user_subject(), _zone()
        p1 = KronicleZonePolicy(subject=subject, access_profile=KronicleZoneAccess(role=_role(), zone=zone))
        p2 = KronicleZonePolicy(subject=subject, access_profile=KronicleZoneAccess(role=_role("reader"), zone=zone))
        assert p1.matches(p2) is False

    def test_matches_false_on_zone(self):
        subject, role = _user_subject(), _role()
        p1 = KronicleZonePolicy(subject=subject, access_profile=KronicleZoneAccess(role=role, zone=_zone("ZoneA")))
        p2 = KronicleZonePolicy(subject=subject, access_profile=KronicleZoneAccess(role=role, zone=_zone("ZoneB")))
        assert p1.matches(p2) is False

    def test_matches_group_subject(self):
        group = KronicleGroup(id=uuid4(), name="Admins")
        subject = KronicleSubject.from_group(group)
        zone, role = _zone(), _role()
        p1 = KronicleZonePolicy(subject=subject, access_profile=KronicleZoneAccess(role=role, zone=zone))
        p2 = KronicleZonePolicy(subject=subject, access_profile=KronicleZoneAccess(role=role, zone=zone))
        assert p1.matches(p2) is True

    def test_flatten(self):
        zone = _zone()
        p = KronicleZonePolicy(subject=_user_subject(), access_profile=KronicleZoneAccess(role=_role(), zone=zone))
        flat = p.flatten()
        assert zone.id is not None
        assert flat["zone_id"] == zone.id.hex
        assert "access_profile" not in flat


class TestKronicleChannelPolicy:
    def test_from_json(self):
        cp = KronicleChannelPolicy.from_json(
            {
                "is_delegation": False,
                "subject": {"type": "user", "name": "subj", "user_id": str(uuid4())},
                "access_profile": {"role": {"name": "writer"}, "channel": {"name": "chan"}},
            }
        )
        assert cp.access_profile.channel.name == "chan"

    def test_matches_true(self):
        subject = _user_subject()
        channel, role = _channel(), _role()
        p1 = KronicleChannelPolicy(subject=subject, access_profile=KronicleChannelAccess(role=role, channel=channel))
        p2 = KronicleChannelPolicy(subject=subject, access_profile=KronicleChannelAccess(role=role, channel=channel))
        assert p1.matches(p2) is True

    def test_matches_false_on_channel(self):
        subject, role = _user_subject(), _role()
        p1 = KronicleChannelPolicy(
            subject=subject, access_profile=KronicleChannelAccess(role=role, channel=_channel("chan1"))
        )
        p2 = KronicleChannelPolicy(
            subject=subject, access_profile=KronicleChannelAccess(role=role, channel=_channel("chan2"))
        )
        assert p1.matches(p2) is False

    def test_flatten(self):
        channel = _channel()
        p = KronicleChannelPolicy(
            subject=_user_subject(), access_profile=KronicleChannelAccess(role=_role(), channel=channel)
        )
        flat = p.flatten()
        assert channel.id is not None
        assert flat["channel_id"] == channel.id.hex
        assert "access_profile" not in flat


class TestKronicleRowPolicy:
    def test_from_json(self):
        rp = KronicleRowPolicy.from_json(
            {
                "is_delegation": False,
                "subject": {"type": "user", "name": "subj", "user_id": str(uuid4())},
                "access_profile": {
                    "role": {"name": "writer"},
                    "row": {"id": 3, "channel_id": str(uuid4()), "name": "test.row"},
                },
            }
        )
        assert rp.access_profile.row.id == 3

    def test_matches_true(self):
        subject = _user_subject()
        row, role = _row(1), _role()
        p1 = KronicleRowPolicy(subject=subject, access_profile=KronicleRowAccess(role=role, row=row))
        p2 = KronicleRowPolicy(subject=subject, access_profile=KronicleRowAccess(role=role, row=row))
        assert p1.matches(p2) is True

    def test_matches_false_on_row(self):
        subject, role = _user_subject(), _role()
        p1 = KronicleRowPolicy(subject=subject, access_profile=KronicleRowAccess(role=role, row=_row(1)))
        p2 = KronicleRowPolicy(subject=subject, access_profile=KronicleRowAccess(role=role, row=_row(2)))
        assert p1.matches(p2) is False

    def test_flatten(self):
        row = _row(7)
        p = KronicleRowPolicy(subject=_user_subject(), access_profile=KronicleRowAccess(role=_role(), row=row))
        flat = p.flatten()
        # NOTE: KronicleRow.id is an int, so uuid_to_str passes it through unchanged.
        assert flat["row_id"] == 7
        assert "access_profile" not in flat
