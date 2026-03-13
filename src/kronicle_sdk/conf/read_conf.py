from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from kronicle_sdk.utils.conf_utils import read_ini_conf
from kronicle_sdk.utils.file_utils import is_file
from kronicle_sdk.utils.log import log_d, log_w


@dataclass
class ConnectionInformation:
    host: str
    port: int

    usr: str
    pwd: str

    @property
    def url(self):
        ssl = self.host not in ["localhost", "127.0.0.1"]
        return f"http{'s' if ssl else ''}://{self.host}:{self.port}"

    @property
    def creds(self):
        return f"{self.usr}{self.pwd}"


class Settings:
    def __init__(self, ini_file: str | None = None):
        here = "conf.init"
        self._conf = None
        if ini_file and is_file(ini_file):
            self._conf = read_ini_conf(ini_file)
            self._section = "kronicle"

        host = self.get_setting(env="KRONICLE_HOST", param="host") or "localhost"
        port = int(self.get_setting(env="KRONICLE_PORT", param="port") or 8000)
        if not host and port:
            log_w(here, "Connection information not found, defaulting to localhost:8000")

        usr = self.get_setting(env="KRONICLE_USR_NAME", param="username")
        pwd = self.get_setting(env="KRONICLE_USR_PASS", param="password")
        if not usr or not pwd:
            raise RuntimeError(
                "Credentials were not found.\n"
                "Please ensure KRONICLE_USR_NAME and KRONICLE_USR_PASS environment variables are set."
            )
        self.connection = ConnectionInformation(host, port, usr, pwd)

        su_usr = self.get_setting(env="KRONICLE_SU_NAME", param="su_username")
        su_pwd = self.get_setting(env="KRONICLE_SU_PASS", param="su_password")
        if su_usr and su_pwd:
            self.connection_su = ConnectionInformation(host, port, su_usr, su_pwd)
        else:
            self.connection_su = None
            log_d(here, "No credentials found for SU.")

    def get_setting(self, *, env: str | None = None, param: str | None = None, default: Any | None = None):
        here = "settings"
        if env:
            env_val = os.getenv(env.upper())
            if env_val:
                # log_d(here, "Extracted from environment variables:", env)
                return env_val
        if self._conf and param:
            conf_val = self._conf.get(self._section, param.lower())
            if conf_val:
                log_d(here, "Extracted from conf file:", param)
                return conf_val
            return None


def get_conf(ini_file: str | None = "./.conf/config.ini"):
    return Settings(ini_file)


if __name__ == "__main__":  # pragma: no cover
    tests = "[conf]"
    conf = get_conf("./.conf/config.ini")
    print(tests, "url:", conf.connection.url)
