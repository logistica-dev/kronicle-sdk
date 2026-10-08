# tests/utils/test_log.py
import re

from kronicle_sdk.utils import log as log_module
from kronicle_sdk.utils.log import decorator_timer, log_assert

TIMESTAMP = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"


class TestLog:
    def test_no_args_prints_timestamp_only(self, capsys):
        log_module.log()
        out = capsys.readouterr().out
        assert re.fullmatch(rf"D {TIMESTAMP}\n", out)

    def test_single_arg_prints_timestamp_only(self, capsys):
        log_module.log("Test log")
        out = capsys.readouterr().out
        assert re.fullmatch(rf"D {TIMESTAMP}\n", out)

    def test_two_args_closes_with_arrow(self, capsys):
        log_module.log("E", "here")
        out = capsys.readouterr().out
        # 'here' is padded to HERE_LEN (15) by enforce_length
        assert re.fullmatch(rf"E {TIMESTAMP} \[{re.escape('here'.ljust(15))}\] <\n", out)

    def test_three_args_prints_message(self, capsys):
        log_module.log("I", "here", "msg")
        out = capsys.readouterr().out
        assert re.fullmatch(rf"I {TIMESTAMP} \[{re.escape('here'.ljust(15))}\] msg\n", out)

    def test_four_plus_args_prints_colon_and_varargs(self, capsys):
        log_module.log("D", "here", "msg", "a", "b")
        out = capsys.readouterr().out
        assert re.fullmatch(rf"D {TIMESTAMP} \[{re.escape('here'.ljust(15))}\] msg: a b\n", out)

    def test_long_here_is_truncated(self, capsys):
        log_module.log("D", "a-very-long-here-value", "msg")
        out = capsys.readouterr().out
        assert "[a-very-long-her]" in out

    def test_should_log_false_prints_nothing(self, capsys, monkeypatch):
        monkeypatch.setattr(log_module, "SHOULD_LOG", False)
        log_module.log("E", "here", "msg")
        assert capsys.readouterr().out == ""


class TestLogLevels:
    def test_log_e_prefixes_error_level(self, capsys):
        log_module.log_e("here", "boom")
        out = capsys.readouterr().out
        assert re.fullmatch(rf"E {TIMESTAMP} \[{re.escape('here'.ljust(15))}\] boom\n", out)

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
