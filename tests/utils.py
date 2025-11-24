from datetime import datetime, timezone
from uuid import uuid4


def now():
    return datetime.now().isoformat()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def now_local():
    return datetime.now().astimezone().isoformat()


def uuid4_str():
    return str(uuid4())


if __name__ == "__main__":
    print("date", "  now_iso:", now_iso())
    print("date", "now_local:", now_local())
    print("date", "      now:", now())
