from time import time

from kronicle_sdk.conf.log_settings import LOG_STR, LogSettings
from kronicle_sdk.utils.str_utils import enforce_length, now_ms

LOG_CONF = LogSettings.read_log_conf()
# LOG_LEVEL = LOG.level
# LOG_FORMAT = LOG.format
# LOG_TZ = LOG.tz

HERE_LEN = 15


def log(*args, **kwargs):  # pragma: no cover
    if LOG_CONF.level < 0:
        return
    if len(args) == 0:
        print()
        return

    log_lvl = args[0]
    log_lvl_str = enforce_length(LOG_STR[log_lvl], 5)

    if LOG_CONF.format == "SYSLOG":
        if len(args) > 1:
            print(now_ms(LOG_CONF.tz), f"[{log_lvl_str}]", f"[{args[1]}]", *args[2:], **kwargs)
        else:
            print(now_ms(LOG_CONF.tz), f"[{log_lvl_str}]")
    else:
        log_letter = log_lvl_str[0]
        if len(args) < 2:
            print(f"{log_letter} {now_ms()}")
            return
        start_line = f"{log_letter} {now_ms()} [{enforce_length(args[1], HERE_LEN)}]"
        if len(args) == 2:
            print(f"{start_line} <")
            return
        if len(args) == 3:
            print(f"{start_line} {args[2]}")
            return
        start_line = f"{start_line} {args[2]}:"
        try:
            print(f"{start_line}", *args[3:])
        except UnicodeDecodeError:
            print(f"{start_line}", str(*args[3:]))


def log_e(*args, **kwargs):  # pragma: no cover
    log(0, *args, **kwargs)


def log_w(*args, **kwargs):  # pragma: no cover
    if LOG_CONF.level > 0:
        log(1, *args, **kwargs)


def log_i(*args, **kwargs):  # pragma: no cover
    if LOG_CONF.level > 1:
        log(2, *args, **kwargs)


def log_d(*args, **kwargs):  # pragma: no cover
    if LOG_CONF.level > 2:
        log(3, *args, **kwargs)


def log_d_if(should_print: bool, *args, **kwargs):  # pragma: no cover
    if should_print:
        log_d(*args)


def decorator_timer(some_function):  # pragma: no cover
    def _wrap(*args, **kwargs):
        multiplier = 50
        begin = time()
        result = None
        for _count in range(multiplier):
            result = some_function(*args, **kwargs)
        duration = (time() - begin) / multiplier
        log_d(some_function.__name__, "duration", duration)
        return result, duration

    return _wrap


def log_assert(cond: bool, ok_tag: str = "OK", ko_tag: str = "!! KO !!"):  # pragma: no cover
    return ok_tag if cond else ko_tag


if __name__ == "__main__":  # pragma: no cover
    log_d()
    log_d("Test")
    log_i("Test log")
    log_w("Log", "Test")
    log_e("Log", "Main", "test")
