# kronicle_sdk/conf/read_conf.py
from __future__ import annotations

import os
from configparser import ConfigParser
from dataclasses import dataclass
from typing import Any

from pydantic import SecretStr

from kronicle_sdk.conf.env_keys import (
    KRONICLE_HOST,
    KRONICLE_PORT,
    KRONICLE_SDK_CONF,
    KRONICLE_SU_CREDS,
    KRONICLE_SU_NAME,
    KRONICLE_SU_PASS,
    KRONICLE_SU_PB64,
    KRONICLE_USR_CREDS,
    KRONICLE_USR_NAME,
    KRONICLE_USR_PASS,
    KRONICLE_USR_PB64,
)
from kronicle_sdk.utils.conf_utils import get_setting, read_ini_conf
from kronicle_sdk.utils.file_utils import is_file
from kronicle_sdk.utils.log import log_d, log_e, log_w
from kronicle_sdk.utils.str_utils import decode_b64url, now_ms


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _decode_pwd_flag(pwd: str, flag_value: bool, here: str) -> str:
    if not flag_value:
        return pwd
    try:
        return decode_b64url(pwd)
    except ValueError as e:
        raise ValueError(f"{here} should be base64url encoded ('is_pwd_b64' is set to True)") from e


def _from_creds(b64_creds) -> tuple[str, str] | None:
    if not b64_creds:
        return
    try:
        creds = decode_b64url(b64_creds).split(":")
    except ValueError as e:
        raise ValueError("Credentials should be base64url encoded") from e
    if len(creds) == 2:
        usr, pwd = creds
        return usr, pwd
    raise ValueError("Incorrect syntax for credentials")


def _extract_creds_from_env(
    creds_env_var: str, usr_env_var: str, pwd_env_var: str, is_b64_env_var: str
) -> tuple[str, str] | None:
    if env_creds := os.getenv(creds_env_var):
        return _from_creds(env_creds)
    usr = os.getenv(usr_env_var)
    pwd = os.getenv(pwd_env_var)
    if not usr or not pwd:
        return None
    if _is_true(os.getenv(is_b64_env_var)):
        pwd = _decode_pwd_flag(pwd, True, f"'{pwd_env_var}'")
    return usr, pwd


def _extract_creds_from_conf(conf: ConfigParser, section: str) -> tuple[str, str] | None:
    if creds := conf.get(section, "credentials", fallback=None):
        return _from_creds(creds)
    usr = conf.get(section, "username", fallback=None)
    pwd = conf.get(section, "password", fallback=None)
    if not usr or not pwd:
        return None
    usr = _strip_quotes(usr)
    pwd = _strip_quotes(pwd)
    is_pwd_b64 = conf.getboolean(section, "is_pwd_b64", fallback=False)
    pwd = _decode_pwd_flag(pwd, is_pwd_b64, f"'password' in section [{section}]")
    return usr, pwd


class Creds:
    def __init__(self, usr: str, pwd: str) -> None:
        self.usr = usr
        self.pwd: SecretStr = SecretStr(pwd)

    @property
    def creds(self):
        return f"{self.usr}:{self.pwd.get_secret_value()}"


@dataclass
class ConnectionInformation:
    host: str
    port: int | None

    usr: str
    pwd: str

    ssl: bool | None = None

    @property
    def _schema(self):
        if self.ssl is None:
            self.ssl = self.host not in ["localhost", "127.0.0.1"]
        return f"http{'s' if self.ssl else ''}"

    @property
    def url(self):
        _port = f":{self.port}" if self.port else ""
        return f"{self._schema}://{self.host}{_port}"

    @property
    def creds(self):
        return f"{self.usr}:{self.pwd}"


class Settings:
    def __init__(self, ini_file: str | None = None):
        self._conf: ConfigParser | None = None
        if ini_file and is_file(ini_file):
            self._conf = read_ini_conf(ini_file)

        host, port = self._extract_server_info()

        usr, pwd = self._extract_usr_creds()
        self.connection = ConnectionInformation(host, port, usr, pwd)
        if su_creds := self._extract_su_creds():
            su_usr, su_pwd = su_creds
            self.connection_su = ConnectionInformation(host, port, su_usr, su_pwd)
        else:
            self.connection_su = None

    def _extract_server_info(self) -> tuple[str, int | None]:
        host = self.get_setting(env=KRONICLE_HOST, section="kronicle_server", param="host")
        _port = self.get_setting(env=KRONICLE_PORT, section="kronicle_server", param="port")
        port = int(_port) if _port else None
        if not host and not port:
            log_w("Settings", "Connection information not found, defaulting to localhost:8000")
            host = "localhost"
            port = 8000
        if not host:
            raise RuntimeError(
                "Host not provided.\nPlease ensure KRONICLE_HOST and KRONICLE_PORT environment variables are set."
            )
        return host, port

    def _extract_usr_creds(self) -> tuple[str, str]:
        env_creds = _extract_creds_from_env(KRONICLE_USR_CREDS, KRONICLE_USR_NAME, KRONICLE_USR_PASS, KRONICLE_USR_PB64)
        if env_creds:
            usr, pwd = env_creds
            return usr, pwd
        if self._conf:
            conf_creds = _extract_creds_from_conf(self._conf, section="kronicle_user")
            if conf_creds:
                usr, pwd = conf_creds
                return usr, pwd
        raise RuntimeError(
            "User credentials were not found.\n"
            "Please ensure KRONICLE_USR_NAME and KRONICLE_USR_PASS environment variables are set."
        )

    def _extract_su_creds(self) -> tuple[str, str] | None:
        try:
            if env_creds := _extract_creds_from_env(
                KRONICLE_SU_CREDS, KRONICLE_SU_NAME, KRONICLE_SU_PASS, KRONICLE_SU_PB64
            ):
                return env_creds
            if self._conf:
                if conf_creds := _extract_creds_from_conf(self._conf, section="kronicle_su"):
                    return conf_creds
        except ValueError as e:
            log_e("Settings", "Incorrect syntax for SU creds, expected base64url encoded usr:pwd:", e)
            return None
        log_d("Settings", "Credentials not found for SU.")
        return None

    def get_setting(
        self,
        *,
        env: str | None = None,
        param: str | None = None,
        section: str | None = None,
        default: Any | None = None,
    ):
        """
        Retrieve a setting from an environment variable or, alternatively, an ini file.
        If both are set, values from ENV are preferred.
        """
        return get_setting(
            env=env,
            conf=self._conf,
            param=param,
            section=section,
            default=default,
        )


def get_conf(ini_file: str | None = None):
    if ini_file:
        return Settings(ini_file)
    return Settings(os.getenv(KRONICLE_SDK_CONF, "./conf/config.ini"))


# SDK_CONF = get_conf()

if __name__ == "__main__":  # pragma: no cover
    tests = "[Kronicle SDK conf]"
    conf = get_conf("./conf/config.ini")
    print(now_ms(), "[DEBUG]", tests, "Kronicle url:", conf.connection.url)
