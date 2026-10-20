# tests/utils/test_conf_utils.py
from configparser import ConfigParser
from os import environ

import pytest

from kronicle_sdk.utils.conf_utils import from_creds, get_setting, load_env, parse_value, read_ini_conf


class TestParseValue:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("true", True),
            ("TRUE", True),
            ("False", False),
            ("  false  ", False),
            ("42", 42),
            ("-7", -7),
            ("3.14", 3.14),
            ('"quoted"', "quoted"),
            ("'single'", "single"),
            ("hello", "hello"),
            ('"unterminated', '"unterminated'),
            ("", ""),
        ],
    )
    def test_inferred_type_and_value(self, raw, expected):
        result = parse_value(raw)
        assert result == expected
        assert type(result) is type(expected)

    def test_quotes_win_over_number(self):
        assert parse_value('"42"') == "42"
        assert isinstance(parse_value('"42"'), str)


class TestReadIniConf:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_ini_conf(str(tmp_path / "missing.ini"))

    def test_basic_read(self, tmp_path):
        conf_file = tmp_path / "app.ini"
        conf_file.write_text("[main]\nname = demo\nport = 8080\n")
        conf = read_ini_conf(str(conf_file))
        assert conf.get("main", "name") == "demo"
        assert conf.getint("main", "port") == 8080

    def test_extended_interpolation(self, tmp_path):
        conf_file = tmp_path / "app.ini"
        conf_file.write_text("[paths]\nroot = /data\n\n[main]\ninput = ${paths:root}/in\n")
        conf = read_ini_conf(str(conf_file))
        assert conf.get("main", "input") == "/data/in"


class TestLoadEnv:
    KEYS = ["KRON_TEST_A", "KRON_TEST_B", "KRON_TEST_C", "KRON_TEST_D", "KRON_TEST_E", "KRON_TEST_F", "KRON_TEST_X"]

    @pytest.fixture(autouse=True)
    def _isolate_environ(self, monkeypatch):
        for key in self.KEYS:
            monkeypatch.delenv(key, raising=False)

    def test_missing_file_returns_empty_dict(self, tmp_path):
        assert load_env(str(tmp_path / ".env")) == {}

    def test_parses_values_and_sets_environ(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# a comment\n"
            "\n"
            "export KRON_TEST_A=hello\n"
            "KRON_TEST_B = 42\n"
            'KRON_TEST_C="1.5"\n'
            "KRON_TEST_D=true\n"
            "KRON_TEST_E='quoted'\n"
            "KRON_TEST_F=a=b\n"
        )
        assert load_env(str(env_file)) == {
            "KRON_TEST_A": "hello",
            "KRON_TEST_B": 42,
            "KRON_TEST_C": "1.5",
            "KRON_TEST_D": True,
            "KRON_TEST_E": "quoted",
            "KRON_TEST_F": "a=b",
        }
        # os.environ always stores strings
        assert environ["KRON_TEST_B"] == "42"
        assert environ["KRON_TEST_D"] == "True"

    def test_existing_env_not_overridden_by_default(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("KRON_TEST_X=from_file\n")
        monkeypatch.setenv("KRON_TEST_X", "existing")

        assert load_env(str(env_file)) == {"KRON_TEST_X": "from_file"}
        assert environ["KRON_TEST_X"] == "existing"

    def test_override_true_replaces_existing(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("KRON_TEST_X=from_file\n")
        monkeypatch.setenv("KRON_TEST_X", "existing")

        load_env(str(env_file), override=True)
        assert environ["KRON_TEST_X"] == "from_file"


class TestFromCreds:
    def test_empty_returns_none(self):
        assert from_creds("") is None
        assert from_creds(None) is None


class TestGetSetting:
    ENV_KEY = "KRON_TEST_SETTING"

    @pytest.fixture(autouse=True)
    def _isolate_env(self, monkeypatch):
        monkeypatch.delenv(self.ENV_KEY, raising=False)

    @pytest.fixture
    def conf(self):
        conf = ConfigParser()
        conf["section"] = {"param": "from_conf", "empty": ""}
        return conf

    def test_env_has_priority(self, monkeypatch, conf):
        monkeypatch.setenv(self.ENV_KEY, "from_env")
        assert get_setting(env=self.ENV_KEY, conf=conf, section="section", param="param") == "from_env"

    def test_falls_back_to_conf(self, conf):
        assert get_setting(env=self.ENV_KEY, conf=conf, section="section", param="param") == "from_conf"

    def test_empty_conf_value_falls_back_to_default(self, conf):
        assert get_setting(env=self.ENV_KEY, conf=conf, section="section", param="empty", default="dflt") == "dflt"

    def test_missing_option_returns_default(self, conf):
        assert get_setting(env=self.ENV_KEY, conf=conf, section="section", param="nope", default="dflt") == "dflt"

    def test_missing_option_without_default_raises(self, conf):
        with pytest.raises(RuntimeError, match="Missing 'nope'"):
            get_setting(env=self.ENV_KEY, conf=conf, section="section", param="nope")

    def test_missing_section_returns_default(self, conf):
        assert get_setting(env=self.ENV_KEY, conf=conf, section="other", param="param", default="dflt") == "dflt"

    def test_missing_section_without_default_raises(self, conf):
        with pytest.raises(RuntimeError, match="Missing config section 'other'"):
            get_setting(env=self.ENV_KEY, conf=conf, section="other", param="param")

    def test_returns_default_without_conf_or_env(self):
        assert get_setting(env=self.ENV_KEY, param="param", default="dflt") == "dflt"

    def test_returns_none_without_anything(self):
        assert get_setting(env=self.ENV_KEY, param="param") is None
