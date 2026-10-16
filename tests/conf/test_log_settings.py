# tests/conf/test_log_settings.py
from configparser import ConfigParser
from datetime import timezone

import pytest

from kronicle_sdk.conf import log_settings as log_settings_module
from kronicle_sdk.conf.env_keys import KRONICLE_SDK_LOG_FORMAT, KRONICLE_SDK_LOG_LEVEL, KRONICLE_SDK_LOG_TZ
from kronicle_sdk.conf.log_settings import LOCAL_TZ, UTC_TZ, LogSettings

DEFAULTS = (3, "SYSLOG", LOCAL_TZ)  # DEBUG / SYSLOG / LOCAL, as documented in env_keys.py


class TestFromUserLevel:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("e", 0),
            ("ERROR", 0),
            ("0", 0),
            ("w", 1),
            ("WARN", 1),
            ("1", 1),
            ("i", 2),
            ("Info", 2),
            ("2", 2),
            ("debug", 3),
            ("3", 3),
            ("NONE", -1),
            ("-1", -1),
            ("4", -1),
            ("verbose", -1),
            ("", -1),
        ],
    )
    def test_levels(self, raw, expected):
        assert LogSettings.from_user_level(raw) == expected

    def test_constructor_coerces_to_int(self):
        assert LogSettings(level="debug").level == 3


class TestFromUserFormat:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("syslog", "SYSLOG"),
            ("SYSLOG", "SYSLOG"),
            ("sys", "SYSLOG"),
            ("dev", "DEV"),
            ("DEV", "DEV"),
            ("json", "DEV"),
            ("", "DEV"),
        ],
    )
    def test_formats(self, raw, expected):
        assert LogSettings.from_user_format(raw) == expected


class TestFromUserTz:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("utc", UTC_TZ),
            ("UTC", UTC_TZ),
            ("local", LOCAL_TZ),
            ("LOCAL", LOCAL_TZ),
            ("none", None),
            ("", None),
            ("paris", None),
        ],
    )
    def test_timezones(self, raw, expected):
        assert LogSettings.from_user_tz(raw) == expected
        assert UTC_TZ is timezone.utc


class TestStrRepresentation:
    @pytest.mark.parametrize(
        ("level", "expected"),
        [(0, "ERROR"), (1, "WARN"), (2, "INFO"), (3, "DEBUG"), (-1, "NONE")],
    )
    def test_level_str(self, level, expected):
        assert LogSettings(level=level).level_str == expected

    def test_str(self):
        s = str(LogSettings(level="error", format="syslog", tz="utc"))
        assert s == "Log level=ERROR | format=SYSLOG | timezone=UTC"


class TestReadLogConf:
    @pytest.fixture(autouse=True)
    def clean_log_env(self, monkeypatch):
        for key in (KRONICLE_SDK_LOG_LEVEL, KRONICLE_SDK_LOG_FORMAT, KRONICLE_SDK_LOG_TZ):
            monkeypatch.delenv(key, raising=False)

    @staticmethod
    def _conf(log_section: dict | None = None) -> ConfigParser:
        conf = ConfigParser()
        if log_section is not None:
            conf["kronicle_sdk_log"] = log_section
        return conf

    @staticmethod
    def _use_conf(monkeypatch, conf: ConfigParser | None):
        monkeypatch.setattr(log_settings_module, "read_conf_file", lambda: conf)

    def test_defaults_without_conf_file(self, monkeypatch):
        self._use_conf(monkeypatch, None)
        s = LogSettings.read_log_conf()
        assert (s.level, s.format, s.tz) == DEFAULTS

    def test_env_is_read_without_conf_file(self, monkeypatch):
        # env vars must work even when no conf file exists (documented in env_keys.py)
        self._use_conf(monkeypatch, None)
        monkeypatch.setenv(KRONICLE_SDK_LOG_LEVEL, "DEBUG")
        s = LogSettings.read_log_conf()
        assert (s.level, s.format, s.tz) == (3, "SYSLOG", LOCAL_TZ)

    def test_defaults_when_conf_has_no_log_section(self, monkeypatch):
        self._use_conf(monkeypatch, self._conf())
        s = LogSettings.read_log_conf()
        assert (s.level, s.format, s.tz) == DEFAULTS

    def test_defaults_when_conf_has_empty_values(self, monkeypatch):
        self._use_conf(monkeypatch, self._conf({"log_level": "", "log_format": "", "log_timezone": ""}))
        s = LogSettings.read_log_conf()
        assert (s.level, s.format, s.tz) == DEFAULTS

    def test_conf_values_are_used(self, monkeypatch):
        self._use_conf(
            monkeypatch,
            self._conf({"log_level": "error", "log_format": "dev", "log_timezone": "utc"}),
        )
        s = LogSettings.read_log_conf()
        assert (s.level, s.format, s.tz) == (0, "DEV", UTC_TZ)

    def test_env_overrides_conf(self, monkeypatch):
        self._use_conf(
            monkeypatch,
            self._conf({"log_level": "debug", "log_format": "syslog", "log_timezone": "utc"}),
        )
        monkeypatch.setenv(KRONICLE_SDK_LOG_LEVEL, "NONE")
        monkeypatch.setenv(KRONICLE_SDK_LOG_FORMAT, "dev")
        monkeypatch.setenv(KRONICLE_SDK_LOG_TZ, "local")
        s = LogSettings.read_log_conf()
        assert (s.level, s.format, s.tz) == (-1, "DEV", LOCAL_TZ)

    def test_none_level_is_silent(self, monkeypatch):
        self._use_conf(monkeypatch, self._conf({"log_level": "NONE"}))
        s = LogSettings.read_log_conf()
        assert s.level == -1
        assert s.level_str == "NONE"
