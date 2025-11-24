from datetime import datetime
from os import getenv
from time import time

SHOULD_LOG = bool(getenv("RUDI_NODE_DEV"))


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(*args):  # pragma: no cover
    if SHOULD_LOG:
        if len(args) < 2:
            print(f"D {_now()}")
        elif len(args) == 2:
            print(f"{args[0]} {_now()} [{args[1]}] <")
        elif len(args) == 3:
            print(f"{args[0]} {_now()} [{args[1]}] {args[2]}")
        else:
            try:
                print(f"{args[0]} {_now()} [{args[1]}] {args[2]}:", *args[3:])
            except UnicodeDecodeError:
                print(f"{args[0]} {_now()} [{args[1]}] {args[2]}:", str(*args[3:]))


def log_e(*args):  # pragma: no cover
    log("E", *args)


def log_w(*args):  # pragma: no cover
    log("W", *args)


def log_d(*args):  # pragma: no cover
    log("D", *args)


def log_d_if(should_print: bool, *args):  # pragma: no cover
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
    log_d("Test log")
    log_d("Log", "Test")
    log_d("Log", "Main", "test")
