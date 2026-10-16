# tests/conf/test_read_conf.py
import os
from configparser import ConfigParser
from unittest.mock import patch

import pytest

from kronicle_sdk.conf.env_keys import (
    KRONICLE_HOST,
    KRONICLE_PORT,
    KRONICLE_SDK_CONF,
    KRONICLE_SDK_LOG_FORMAT,
    KRONICLE_SDK_LOG_LEVEL,
    KRONICLE_SDK_LOG_TZ,
    KRONICLE_SU_CREDS,
    KRONICLE_SU_NAME,
    KRONICLE_SU_PASS,
    KRONICLE_SU_PB64,
    KRONICLE_USR_CREDS,
    KRONICLE_USR_NAME,
    KRONICLE_USR_PASS,
    KRONICLE_USR_PB64,
)
from kronicle_sdk.conf.read_conf import ConnectionInformation, Creds, Settings, _from_creds, get_conf
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
        assert conn.creds == "user:pass"


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
    KRONICLE_SDK_CONF,
    KRONICLE_SDK_LOG_LEVEL,
    KRONICLE_SDK_LOG_FORMAT,
    KRONICLE_SDK_LOG_TZ,
    KRONICLE_USR_CREDS,
    KRONICLE_USR_NAME,
    KRONICLE_USR_PASS,
    KRONICLE_USR_PB64,
    KRONICLE_SU_CREDS,
    KRONICLE_SU_NAME,
    KRONICLE_SU_PASS,
    KRONICLE_SU_PB64,
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
        conf_parser["kronicle_server"] = {
            "host": "filehost",
            "port": "4321",
        }
        conf_parser["kronicle_user"] = {
            "username": "fileuser",
            "password": "filepass",
        }
        conf_parser["kronicle_su"] = {
            "username": "sufileuser",
            "password": "sufilepass",
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
        conf_parser["kronicle_server"] = {"host": "filehost"}
        s._conf = conf_parser
        val = s.get_setting(env=KRONICLE_HOST, section="kronicle_server", param="host")
        assert val == "envhost"

    def test_get_setting_fallback_to_conf(self, monkeypatch):
        if KRONICLE_USR_NAME not in os.environ:
            monkeypatch.setenv(KRONICLE_USR_NAME, "envuser")
        if KRONICLE_USR_PASS not in os.environ:
            monkeypatch.setenv(KRONICLE_USR_PASS, "envpass")
        s = Settings(None)
        conf_parser = ConfigParser()
        conf_parser["kronicle_server"] = {"host": "filehost"}
        s._conf = conf_parser
        val = s.get_setting(env="NON_EXISTENT_ENV", section="kronicle_server", param="host")
        assert val == "filehost"

    def test_get_setting_returns_none_when_missing(self, monkeypatch):
        if KRONICLE_USR_NAME not in os.environ:
            monkeypatch.setenv(KRONICLE_USR_NAME, "envuser")
        if KRONICLE_USR_PASS not in os.environ:
            monkeypatch.setenv(KRONICLE_USR_PASS, "envpass")
        s = Settings(None)
        conf_parser = ConfigParser()
        conf_parser["kronicle_server"] = {}
        s._conf = conf_parser
        assert s.get_setting(env="NON_EXISTENT") is None
        with pytest.raises(RuntimeError, match="Missing 'missing'"):
            s.get_setting(env="NON_EXISTENT", section="kronicle_server", param="missing")

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
        conf_parser["kronicle_server"] = {"host": ""}
        s._conf = conf_parser
        assert s.get_setting(env="NON_EXISTENT_ENV", section="kronicle_server", param="host", default="fallback") == (
            "fallback"
        )
        assert s.get_setting(env="NON_EXISTENT_ENV", section="kronicle_server", param="host") is None


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
        # No [kronicle_su] section: the SU lookup finds nothing and stays None.
        conf_parser = ConfigParser()
        conf_parser["kronicle_server"] = {
            "host": "filehost",
            "port": "4321",
        }
        conf_parser["kronicle_user"] = {
            "username": "fileuser",
            "password": "filepass",
        }
        with patch("kronicle_sdk.conf.read_conf.read_ini_conf", return_value=conf_parser):
            s = Settings("./somefile.ini")
        assert s.connection.host == "filehost"
        assert s.connection.port == 4321
        assert s.connection.usr == "fileuser"
        assert s.connection.pwd == "filepass"
        assert s.connection_su is None


def test_get_conf_factory(monkeypatch):
    monkeypatch.setenv(KRONICLE_USR_NAME, "envuser")
    monkeypatch.setenv(KRONICLE_USR_PASS, "envpass")
    conf = get_conf()
    assert isinstance(conf, Settings)
    assert conf.connection.usr == "envuser"


def test_get_conf_factory_with_ini_file(monkeypatch):
    monkeypatch.setenv(KRONICLE_USR_NAME, "envuser")
    monkeypatch.setenv(KRONICLE_USR_PASS, "envpass")
    conf_parser = ConfigParser()
    conf_parser["kronicle_server"] = {"host": "localhost", "port": "8000"}
    with (
        patch("kronicle_sdk.conf.read_conf.is_file", return_value=True),
        patch("kronicle_sdk.conf.read_conf.read_ini_conf", return_value=conf_parser),
    ):
        conf = get_conf("./somefile.ini")
    assert isinstance(conf, Settings)
    assert conf.connection.host == "localhost"


class TestCreds:
    def test_creds_property(self):
        assert Creds("user", "pass").creds == "user:pass"

    def test_pwd_hidden_from_repr(self):
        assert "pass" not in repr(Creds("user", "pass"))


class TestFromCreds:
    def test_empty_returns_none(self):
        assert _from_creds("") is None
        assert _from_creds(None) is None


class TestPwdB64Flag:
    """Password decoding driven by KRONICLE_USR_PB64 (env) or is_pwd_b64 (conf)."""

    @pytest.fixture
    def conf_env(self, clean_env, monkeypatch):
        """Server info from ENV so the conf file only carries credentials."""
        monkeypatch.setenv(KRONICLE_HOST, "envhost")
        monkeypatch.setenv(KRONICLE_PORT, "1234")

    @staticmethod
    def _settings_from(conf_parser: ConfigParser) -> Settings:
        with (
            patch("kronicle_sdk.conf.read_conf.is_file", return_value=True),
            patch("kronicle_sdk.conf.read_conf.read_ini_conf", return_value=conf_parser),
        ):
            return Settings("./somefile.ini")

    # --- env-driven ---------------------------------------------------------
    def test_env_plain_password_with_false_flag(self, base_env, monkeypatch):
        monkeypatch.delenv(KRONICLE_USR_CREDS, raising=False)
        monkeypatch.setenv(KRONICLE_USR_PASS, "plain-pwd")
        monkeypatch.setenv(KRONICLE_USR_PB64, "False")
        s = Settings(None)
        assert s.connection.pwd == "plain-pwd"

    def test_env_plain_password_without_flag(self, base_env, monkeypatch):
        monkeypatch.delenv(KRONICLE_USR_CREDS, raising=False)
        monkeypatch.setenv(KRONICLE_USR_PASS, "plain-pwd")
        s = Settings(None)
        assert s.connection.pwd == "plain-pwd"

    def test_env_b64_password_decoded(self, base_env, monkeypatch):
        monkeypatch.delenv(KRONICLE_USR_CREDS, raising=False)
        monkeypatch.setenv(KRONICLE_USR_PASS, encode_b64url("s3cret"))
        monkeypatch.setenv(KRONICLE_USR_PB64, "True")
        s = Settings(None)
        assert s.connection.pwd == "s3cret"

    def test_env_b64_flag_with_invalid_b64_raises(self, base_env, monkeypatch):
        monkeypatch.delenv(KRONICLE_USR_CREDS, raising=False)
        monkeypatch.setenv(KRONICLE_USR_PASS, "not b64!!")
        monkeypatch.setenv(KRONICLE_USR_PB64, "yes")
        with pytest.raises(ValueError, match="base64url"):
            Settings(None)

    # --- conf-driven --------------------------------------------------------
    def test_conf_plain_password_with_false_flag(self, conf_env):
        conf_parser = ConfigParser()
        conf_parser["kronicle_user"] = {"username": "fileuser", "password": "plain-pwd", "is_pwd_b64": "False"}
        s = self._settings_from(conf_parser)
        assert s.connection.pwd == "plain-pwd"

    def test_conf_plain_password_without_flag(self, conf_env):
        conf_parser = ConfigParser()
        conf_parser["kronicle_user"] = {"username": "fileuser", "password": "plainpwd"}
        s = self._settings_from(conf_parser)
        assert s.connection.pwd == "plainpwd"

    def test_conf_b64_password_decoded(self, conf_env):
        conf_parser = ConfigParser()
        conf_parser["kronicle_user"] = {
            "username": "fileuser",
            "password": encode_b64url("s3cret"),
            "is_pwd_b64": "True",
        }
        s = self._settings_from(conf_parser)
        assert s.connection.pwd == "s3cret"

    def test_conf_b64_flag_with_invalid_b64_raises(self, conf_env):
        conf_parser = ConfigParser()
        conf_parser["kronicle_user"] = {"username": "fileuser", "password": "not b64!!", "is_pwd_b64": "True"}
        with pytest.raises(ValueError, match="base64url"):
            self._settings_from(conf_parser)

    def test_conf_credentials_option_takes_precedence(self, conf_env):
        conf_parser = ConfigParser()
        conf_parser["kronicle_user"] = {
            "credentials": encode_b64url("b64user:b64pass"),
            "username": "fileuser",
            "password": "filepass",
        }
        s = self._settings_from(conf_parser)
        assert s.connection.usr == "b64user"
        assert s.connection.pwd == "b64pass"

    def test_conf_without_credentials_option_falls_back_to_username_password(self, conf_env):
        # Deleting the 'credentials' line (the documented alternative) must not break the lookup.
        conf_parser = ConfigParser()
        conf_parser["kronicle_user"] = {"username": "fileuser", "password": "filepass"}
        s = self._settings_from(conf_parser)
        assert s.connection.usr == "fileuser"
        assert s.connection.pwd == "filepass"

    def test_conf_quotes_are_stripped(self, conf_env):
        conf_parser = ConfigParser()
        conf_parser["kronicle_user"] = {"username": '"MyUser"', "password": '"All cats are beautiful!"'}
        s = self._settings_from(conf_parser)
        assert s.connection.usr == "MyUser"
        assert s.connection.pwd == "All cats are beautiful!"

    def test_conf_username_without_password_raises(self, conf_env):
        conf_parser = ConfigParser()
        conf_parser["kronicle_user"] = {"username": "fileuser"}
        with pytest.raises(RuntimeError, match="credentials were not found"):
            self._settings_from(conf_parser)
