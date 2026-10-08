# tests/utils/test_file_utils.py
import os

import pytest

from kronicle_sdk.utils.file_utils import (
    ACCEPTED_HASH_ALGOS,
    check_is_dir,
    check_is_file,
    exists_file,
    expand_file_path,
    get_file_size,
    is_dir,
    is_file,
    load_env_file,
    make_dir,
    read_json_file,
    write_file,
    write_json_file,
)


class TestPathChecks:
    def test_is_dir(self, tmp_path):
        assert is_dir(str(tmp_path))
        assert not is_dir(str(tmp_path / "nope"))

    def test_check_is_dir_returns_path(self, tmp_path):
        assert check_is_dir(str(tmp_path)) == str(tmp_path)

    def test_check_is_dir_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="No such file"):
            check_is_dir(str(tmp_path / "nope"))

    def test_check_is_dir_custom_message(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="custom dir message"):
            check_is_dir(str(tmp_path / "nope"), err_msg="custom dir message")

    def test_exists_file_vs_is_file(self, tmp_path):
        # a directory exists but is not a file
        assert exists_file(str(tmp_path))
        assert not is_file(str(tmp_path))

        f = tmp_path / "a.txt"
        f.write_text("x")
        assert exists_file(str(f))
        assert is_file(str(f))

    def test_check_is_file_returns_path(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("x")
        assert check_is_file(str(f)) == str(f)

    def test_check_is_file_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="No such file"):
            check_is_file(str(tmp_path / "missing.txt"))

    def test_check_is_file_custom_message(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="custom file message"):
            check_is_file(str(tmp_path / "missing.txt"), err_msg="custom file message")


class TestMakeDir:
    def test_creates_nested_dir(self, tmp_path):
        target = tmp_path / "a" / "b" / "c"
        assert make_dir(str(target)) == str(target)
        assert target.is_dir()

    def test_existing_dir_is_noop(self, tmp_path):
        assert make_dir(str(tmp_path)) == str(tmp_path)

    def test_existing_file_raises(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("x")
        with pytest.raises(FileNotFoundError):
            make_dir(str(f))


class TestExpandFilePath:
    def test_expands_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        assert expand_file_path("~/docs/a.txt") == str(tmp_path / "docs" / "a.txt")

    def test_makes_relative_paths_absolute(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert expand_file_path("sub/f.txt") == str(tmp_path / "sub" / "f.txt")


class TestFileSize:
    def test_get_file_size(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("hello")
        assert get_file_size(str(f)) == 5


class TestJsonFiles:
    def test_read_json_file(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"a": 1, "list": [1, 2]}')
        assert read_json_file(str(f)) == {"a": 1, "list": [1, 2]}

    def test_read_json_file_binary_mode(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"a": 1}')
        assert read_json_file(str(f), mode="b") == {"a": 1}

    def test_read_json_file_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_json_file(str(tmp_path / "missing.json"))

    def test_write_json_file_roundtrip(self, tmp_path):
        f = tmp_path / "out.json"
        write_json_file(str(f), {"name": "café", "n": 1})
        assert read_json_file(str(f)) == {"name": "café", "n": 1}


class TestWriteFile:
    def test_text_mode(self, tmp_path):
        f = tmp_path / "out.txt"
        write_file(str(f), "hello")
        assert f.read_text() == "hello"

    def test_binary_mode(self, tmp_path):
        f = tmp_path / "out.bin"
        write_file(str(f), b"hello", mode="b")
        assert f.read_bytes() == b"hello"


class TestLoadEnvFile:
    ENV_KEYS = ["LOAD_ENV_A", "LOAD_ENV_B", "LOAD_ENV_C", "LOAD_ENV_D"]

    @pytest.fixture(autouse=True)
    def _isolate_environ(self, monkeypatch):
        for key in self.ENV_KEYS:
            monkeypatch.delenv(key, raising=False)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_env_file(tmp_path / ".env")

    def test_sets_environ(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# comment\n"
            "LOAD_ENV_A=plain\n"
            'LOAD_ENV_B = "quoted value"\n'
            "export LOAD_ENV_C='single'\n"
            "no_equal_sign_here\n"
            "LOAD_ENV_D=trailing  \n"
        )
        load_env_file(env_file)
        assert os.environ["LOAD_ENV_A"] == "plain"
        assert os.environ["LOAD_ENV_B"] == "quoted value"
        assert os.environ["LOAD_ENV_C"] == "single"
        assert os.environ["LOAD_ENV_D"] == "trailing"
        assert "no_equal_sign_here" not in os.environ


class TestConstants:
    def test_accepted_hash_algos(self):
        assert ACCEPTED_HASH_ALGOS == ("MD5", "SHA-256", "SHA256", "SHA-512", "SHA512")
