# kronicle_sdk/conf/log_settings.py
from __future__ import annotations

from datetime import datetime, timezone, tzinfo
from typing import Any, Literal

from kronicle_sdk.conf.env_keys import KRONICLE_SDK_LOG_FORMAT, KRONICLE_SDK_LOG_LEVEL, KRONICLE_SDK_LOG_TZ
from kronicle_sdk.utils.conf_utils import get_setting, read_conf_file
from kronicle_sdk.utils.str_utils import now_ms

LOCAL_TZ = datetime.now().astimezone().tzinfo
UTC_TZ = timezone.utc
LOG_STR = ["ERROR", "WARN", "INFO", "DEBUG", "NONE"]


class LogSettings:
    def __init__(self, level: Any, format: Any = None, tz: Any = None) -> None:
        self.level: int = self.from_user_level(f"{level}")
        self.format: Literal["SYSLOG", "DEV"] = self.from_user_format(f"{format}")
        self.tz: tzinfo | None = self.from_user_tz(f"{tz}")

    @property
    def level_str(self) -> str:
        return LOG_STR[self.level]

    @staticmethod
    def from_user_level(level: str):
        if level.lower().startswith("e") or level == "0":
            return 0
        if level.lower().startswith("w") or level == "1":
            return 1
        if level.lower().startswith("i") or level == "2":
            return 2
        if level.lower().startswith("d") or level == "3":
            return 3
        return -1

    @staticmethod
    def from_user_format(format: str):
        return "SYSLOG" if format.lower().startswith("sys") else "DEV"

    @staticmethod
    def from_user_tz(tz: str) -> tzinfo | None:
        if tz.lower() == ("utc"):
            return UTC_TZ
        if tz.lower() == ("local"):
            return LOCAL_TZ

    def __str__(self) -> str:
        return f"Log level={self.level_str} | format={self.format} | timezone={self.tz}"

    @classmethod
    def read_log_conf(cls):
        conf = read_conf_file()
        section = "kronicle_sdk_log"
        level = get_setting(env=KRONICLE_SDK_LOG_LEVEL, conf=conf, section=section, param="log_level", default="DEBUG")
        format = get_setting(
            env=KRONICLE_SDK_LOG_FORMAT, conf=conf, section=section, param="log_format", default="SYSLOG"
        )
        tz = get_setting(env=KRONICLE_SDK_LOG_TZ, conf=conf, section=section, param="log_timezone", default="LOCAL")
        return cls(level, format, tz)


if __name__ == "__main__":  # pragma: no cover
    tests = "[Kronicle SDK conf]"
    log_conf = LogSettings.read_log_conf()
    print(now_ms(), "[DEBUG]", tests, "Kronicle url:", log_conf)
