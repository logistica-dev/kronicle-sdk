# tests/utils/test_log.py
import re

import pytest

from kronicle_sdk.conf.log_settings import LogSettings
from kronicle_sdk.utils import log as log_module
from kronicle_sdk.utils.log import decorator_timer, log_assert

# now_ms() renders 'YYYY-MM-DD HH:MM:SS.mmm', with a '±HH:MM' offset when a tz is applied
TIMESTAMP = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}(?:[+-]\d{2}:\d{2})?"

HERE = "here".ljust(15)  # padded to HERE_LEN by enforce_length


@pytest.fixture(autouse=True)
def dev_debug_conf(monkeypatch):
    """Pin LOG_CONF so output does not depend on the conf file found in the cwd."""
    monkeypatch.setattr(log_module, "LOG_CONF", LogSettings(level=3, format="DEV"))


class TestLog:
    def test_no_args_prints_blank_line(self, capsys):
        log_module.log()
        assert capsys.readouterr().out == "\n"

    def test_level_only_prints_letter_and_timestamp(self, capsys):
        log_module.log(3)
        out = capsys.readouterr().out
        assert re.fullmatch(rf"D {TIMESTAMP}\n", out)

    def test_two_args_closes_with_arrow(self, capsys):
        log_module.log(0, "here")
        out = capsys.readouterr().out
        assert re.fullmatch(rf"E {TIMESTAMP} \[{re.escape(HERE)}\] <\n", out)

    def test_three_args_prints_message(self, capsys):
        log_module.log(2, "here", "msg")
        out = capsys.readouterr().out
        assert re.fullmatch(rf"I {TIMESTAMP} \[{re.escape(HERE)}\] msg\n", out)

    def test_four_plus_args_prints_colon_and_varargs(self, capsys):
        log_module.log(3, "here", "msg", "a", "b")
        out = capsys.readouterr().out
        assert re.fullmatch(rf"D {TIMESTAMP} \[{re.escape(HERE)}\] msg: a b\n", out)

    def test_long_here_is_truncated(self, capsys):
        log_module.log(3, "a-very-long-here-value", "msg")
        out = capsys.readouterr().out
        assert "[a-very-long-her]" in out

    def test_nothing_printed_when_level_is_none(self, capsys, monkeypatch):
        monkeypatch.setattr(log_module, "LOG_CONF", LogSettings(level=-1))
        log_module.log(0, "here", "msg")
        log_module.log()
        assert capsys.readouterr().out == ""


class TestLogLevels:
    def test_log_e_prefixes_error_level(self, capsys):
        log_module.log_e("here", "boom")
        out = capsys.readouterr().out
        assert re.fullmatch(rf"E {TIMESTAMP} \[{re.escape(HERE)}\] boom\n", out)

    def test_log_w_prefixes_warning_level(self, capsys):
        log_module.log_w("here", "careful")
        assert capsys.readouterr().out.startswith("W ")

    def test_log_i_prefixes_info_level(self, capsys):
        log_module.log_i("here", "fyi")
        assert capsys.readouterr().out.startswith("I ")

    def test_log_d_prefixes_debug_level(self, capsys):
        log_module.log_d("Log", "Main", "test")
        out = capsys.readouterr().out
        assert re.fullmatch(rf"D {TIMESTAMP} \[{re.escape('Log'.ljust(15))}\] Main: test\n", out)

    def test_log_d_no_args(self, capsys):
        log_module.log_d()
        assert re.fullmatch(rf"D {TIMESTAMP}\n", capsys.readouterr().out)


class TestLevelGating:
    @pytest.mark.parametrize(
        ("level", "emitted", "suppressed"),
        [
            (0, "log_e", "log_w"),  # ERROR: only log_e
            (1, "log_w", "log_i"),  # WARN: log_e + log_w
            (2, "log_i", "log_d"),  # INFO: log_e + log_w + log_i
        ],
    )
    def test_level_gates_wrappers(self, monkeypatch, capsys, level, emitted, suppressed):
        monkeypatch.setattr(log_module, "LOG_CONF", LogSettings(level=level))
        getattr(log_module, emitted)("here", "msg")
        assert capsys.readouterr().out != ""
        if suppressed:
            getattr(log_module, suppressed)("here", "msg")
            assert capsys.readouterr().out == ""


class TestSyslogFormat:
    @pytest.fixture(autouse=True)
    def syslog_conf(self, monkeypatch):
        monkeypatch.setattr(log_module, "LOG_CONF", LogSettings(level=3, format="SYSLOG", tz="UTC"))

    def test_message_with_here_and_varargs(self, capsys):
        log_module.log_d("Log", "Main", "test")
        out = capsys.readouterr().out
        assert re.fullmatch(rf"{TIMESTAMP} \[DEBUG\] \[Log\] Main test\n", out)

    def test_level_only(self, capsys):
        log_module.log_w()
        out = capsys.readouterr().out
        assert re.fullmatch(rf"{TIMESTAMP} \[WARN \]\n", out)

    def test_nothing_printed_when_disabled(self, capsys, monkeypatch):
        monkeypatch.setattr(log_module, "LOG_CONF", LogSettings(level=-1, format="SYSLOG", tz="UTC"))
        log_module.log_e("here", "boom")
        assert capsys.readouterr().out == ""


class TestLogDIf:
    def test_true_prints(self, capsys):
        log_module.log_d_if(True, "here", "msg")
        assert capsys.readouterr().out != ""

    def test_false_prints_nothing(self, capsys):
        log_module.log_d_if(False, "here", "msg")
        assert capsys.readouterr().out == ""


class TestLogAssert:
    def test_ok_tags(self):
        assert log_assert(True) == "OK"
        assert log_assert(False) == "!! KO !!"

    def test_custom_tags(self):
        assert log_assert(1 == 1, ok_tag="yes", ko_tag="no") == "yes"
        assert log_assert(1 == 2, ok_tag="yes", ko_tag="no") == "no"


class TestDecoratorTimer:
    def test_returns_result_and_duration(self, capsys):
        calls = []

        @decorator_timer
        def double(x):
            calls.append(x)
            return x * 2

        result, duration = double(21)
        assert result == 42
        assert len(calls) == 50  # function is run `multiplier` times
        assert duration >= 0
        assert "duration" in capsys.readouterr().out
