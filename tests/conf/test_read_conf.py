# tests/conf/test_read_conf.py
import os
from configparser import ConfigParser
from unittest.mock import patch

import pytest

from kronicle_sdk.conf.env_keys import (
    KRONICLE_HOST,
    KRONICLE_PORT,
    KRONICLE_SU_CREDS,
    KRONICLE_SU_NAME,
    KRONICLE_SU_PASS,
    KRONICLE_USR_NAME,
    KRONICLE_USR_PASS,
)
from kronicle_sdk.conf.read_conf import ConnectionInformation, Settings, get_conf
from kronicle_sdk.utils.str_utils import encode_b64url


class TestConnectionInformation:
    def test_url_http_for_localhost(self):
        conn = ConnectionInformation(host="localhost", port=8000, usr="u", pwd="p")
        assert conn.url == "http://localhost:8000"

    def test_url_https_for_remote_host(self):
        conn = ConnectionInformation(host="remotehost", port=443, usr="u", pwd="p")
        assert conn.url == "https://remotehost:443"

    def test_creds_property(self):
        conn = ConnectionInformation(host="h", port=1, usr="user", pwd="pass")
        assert conn.creds == "userpass"


@pytest.fixture
def env_vars(monkeypatch):
    monkeypatch.setenv(KRONICLE_HOST, "envhost")
    monkeypatch.setenv(KRONICLE_PORT, "1234")
    monkeypatch.setenv(KRONICLE_USR_NAME, "envuser")
    monkeypatch.setenv(KRONICLE_USR_PASS, "envpass")
    monkeypatch.setenv(KRONICLE_SU_NAME, "suuser")
    monkeypatch.setenv(KRONICLE_SU_PASS, "supass")


@pytest.fixture
def no_su_env(monkeypatch):
    monkeypatch.setenv(KRONICLE_USR_NAME, "envuser")
    monkeypatch.setenv(KRONICLE_USR_PASS, "envpass")
    monkeypatch.delenv(KRONICLE_SU_NAME, raising=False)
    monkeypatch.delenv(KRONICLE_SU_PASS, raising=False)


ALL_KRONICLE_KEYS = (
    KRONICLE_HOST,
    KRONICLE_PORT,
    KRONICLE_USR_NAME,
    KRONICLE_USR_PASS,
    KRONICLE_SU_NAME,
    KRONICLE_SU_PASS,
    KRONICLE_SU_CREDS,
)


@pytest.fixture
def clean_env(monkeypatch):
    """Remove every KRONICLE_* key so ambient env cannot leak into the test."""
    for key in ALL_KRONICLE_KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def base_env(clean_env, monkeypatch):
    """Connection info from ENV, with every superuser key cleared."""
    monkeypatch.setenv(KRONICLE_HOST, "envhost")
    monkeypatch.setenv(KRONICLE_PORT, "1234")
    monkeypatch.setenv(KRONICLE_USR_NAME, "envuser")
    monkeypatch.setenv(KRONICLE_USR_PASS, "envpass")


class TestSettings:
    @patch("kronicle_sdk.conf.read_conf.is_file", return_value=True)
    def test_env_overrides_file(self, mock_is_file, monkeypatch):
        """
        Environment variables take priority over the INI file, even if the file exists.
        """
        conf_parser = ConfigParser()
        conf_parser["kronicle"] = {
            "host": "filehost",
            "port": "4321",
            "username": "fileuser",
            "password": "filepass",
            "su_username": "sufileuser",
            "su_password": "sufilepass",
        }

        with patch("kronicle_sdk.conf.read_conf.read_ini_conf", return_value=conf_parser):
            monkeypatch.setenv(KRONICLE_HOST, "envhost")
            monkeypatch.setenv(KRONICLE_PORT, "1234")
            monkeypatch.setenv(KRONICLE_USR_NAME, "envuser")
            monkeypatch.setenv(KRONICLE_USR_PASS, "envpass")
            monkeypatch.setenv(KRONICLE_SU_NAME, "suenvuser")
            monkeypatch.setenv(KRONICLE_SU_PASS, "suenvpass")

            s = Settings("./somefile.ini")

        # ENV variables override file values
        assert s.connection.host == "envhost"
        assert s.connection.port == 1234
        assert s.connection.usr == "envuser"
        assert s.connection.pwd == "envpass"

        # Superuser ENV overrides file safely
        assert s.connection_su and s.connection_su.usr == "suenvuser"
        assert s.connection_su and s.connection_su.pwd == "suenvpass"

    def test_reads_from_env(self, env_vars):
        s = Settings(None)
        assert s.connection.host == "envhost"
        assert s.connection.port == 1234
        assert s.connection.usr == "envuser"
        assert s.connection.pwd == "envpass"
        assert s.connection_su and s.connection_su.usr == "suuser"
        assert s.connection_su and s.connection_su.pwd == "supass"

    def test_no_su_credentials(self, no_su_env):
        s = Settings(None)
        assert s.connection_su is None

    def test_missing_credentials_raises(self, monkeypatch):
        monkeypatch.delenv(KRONICLE_USR_NAME, raising=False)
        monkeypatch.delenv(KRONICLE_USR_PASS, raising=False)
        with pytest.raises(RuntimeError):
            Settings(None)

    def test_default_host_port_when_missing(self, monkeypatch):
        monkeypatch.setenv(KRONICLE_USR_NAME, "user")
        monkeypatch.setenv(KRONICLE_USR_PASS, "pass")
        monkeypatch.delenv(KRONICLE_HOST, raising=False)
        monkeypatch.delenv(KRONICLE_PORT, raising=False)
        s = Settings(None)
        assert s.connection.host == "localhost"
        assert s.connection.port == 8000

    def test_get_setting_priority_env_over_conf(self, monkeypatch):
        monkeypatch.setenv(KRONICLE_HOST, "envhost")
        if KRONICLE_USR_NAME not in os.environ:
            monkeypatch.setenv(KRONICLE_USR_NAME, "envuser")
        if KRONICLE_USR_PASS not in os.environ:
            monkeypatch.setenv(KRONICLE_USR_PASS, "envpass")
        s = Settings(None)
        conf_parser = ConfigParser()
        conf_parser["kronicle"] = {"host": "filehost"}
        s._conf = conf_parser
        s._section = "kronicle"
        val = s.get_setting(env=KRONICLE_HOST, param="host")
        assert val == "envhost"

    def test_get_setting_fallback_to_conf(self, monkeypatch):
        if KRONICLE_USR_NAME not in os.environ:
            monkeypatch.setenv(KRONICLE_USR_NAME, "envuser")
        if KRONICLE_USR_PASS not in os.environ:
            monkeypatch.setenv(KRONICLE_USR_PASS, "envpass")
        s = Settings(None)
        conf_parser = ConfigParser()
        conf_parser["kronicle"] = {"host": "filehost"}
        s._conf = conf_parser
        s._section = "kronicle"
        val = s.get_setting(env="NON_EXISTENT_ENV", param="host")
        assert val == "filehost"

    def test_get_setting_returns_none_when_missing(self, monkeypatch):
        if KRONICLE_USR_NAME not in os.environ:
            monkeypatch.setenv(KRONICLE_USR_NAME, "envuser")
        if KRONICLE_USR_PASS not in os.environ:
            monkeypatch.setenv(KRONICLE_USR_PASS, "envpass")
        s = Settings(None)
        conf_parser = ConfigParser()
        conf_parser["kronicle"] = {}
        s._conf = conf_parser
        s._section = "kronicle"
        assert s.get_setting(env="NON_EXISTENT") is None
        with pytest.raises(RuntimeError):
            s.get_setting(env="NON_EXISTENT", param="missing")

    def test_missing_host_with_port_raises(self, monkeypatch):
        # port set but no host: the localhost default does not kick in
        monkeypatch.delenv(KRONICLE_HOST, raising=False)
        monkeypatch.setenv(KRONICLE_PORT, "8000")
        monkeypatch.setenv(KRONICLE_USR_NAME, "envuser")
        monkeypatch.setenv(KRONICLE_USR_PASS, "envpass")
        with pytest.raises(RuntimeError, match="Host not provided"):
            Settings(None)

    def test_get_setting_empty_conf_value_returns_default(self, base_env):
        s = Settings(None)
        conf_parser = ConfigParser()
        conf_parser["kronicle"] = {"host": ""}
        s._conf = conf_parser
        s._section = "kronicle"
        assert s.get_setting(env="NON_EXISTENT_ENV", param="host", default="fallback") == "fallback"
        assert s.get_setting(env="NON_EXISTENT_ENV", param="host") is None


class TestSuperUserCredentials:
    def test_from_b64_usr_pwd(self, base_env, monkeypatch):
        monkeypatch.setenv(KRONICLE_SU_CREDS, encode_b64url("b64user:b64pass"))
        s = Settings(None)
        assert s.connection_su is not None
        assert s.connection_su.host == "envhost"
        assert s.connection_su.port == 1234
        assert s.connection_su.usr == "b64user"
        assert s.connection_su.pwd == "b64pass"

    def test_invalid_b64_returns_none(self, base_env, monkeypatch):
        monkeypatch.setenv(KRONICLE_SU_CREDS, "not_valid!!")
        s = Settings(None)
        assert s.connection_su is None

    def test_missing_colon_returns_none(self, base_env, monkeypatch):
        monkeypatch.setenv(KRONICLE_SU_CREDS, encode_b64url("nocolon"))
        s = Settings(None)
        assert s.connection_su is None

    @patch("kronicle_sdk.conf.read_conf.is_file", return_value=True)
    def test_su_options_missing_from_conf_fall_back(self, mock_is_file, clean_env):
        # No su_username/su_password/su_creds options: both lookups raise and
        # are swallowed, leaving no superuser connection.
        conf_parser = ConfigParser()
        conf_parser["kronicle"] = {
            "host": "filehost",
            "port": "4321",
            "username": "fileuser",
            "password": "filepass",
        }
        with patch("kronicle_sdk.conf.read_conf.read_ini_conf", return_value=conf_parser):
            s = Settings("./somefile.ini")
        assert s.connection.host == "filehost"
        assert s.connection.port == 4321
        assert s.connection.usr == "fileuser"
        assert s.connection_su is None


def test_get_conf_factory(monkeypatch):
    monkeypatch.setenv(KRONICLE_USR_NAME, "envuser")
    monkeypatch.setenv(KRONICLE_USR_PASS, "envpass")
    conf = get_conf()
    assert isinstance(conf, Settings)
    assert conf.connection.usr == "envuser"
