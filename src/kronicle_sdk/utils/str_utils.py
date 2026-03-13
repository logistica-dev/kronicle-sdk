from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime
from random import choices
from re import compile, sub
from string import ascii_lowercase, digits
from typing import Any, Literal
from uuid import UUID, uuid4

REGEX_UUID = compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def enforce_length(here: str, length=12) -> str:
    return here.ljust(length, " ") if len(here) < length else here[0:length]


def slash_join(*args) -> str:
    """
    Joins a set of strings with a slash (/) between them (useful for merging URLs or paths fragments)
    """
    non_null_args = []
    for frag in args:
        if frag is None or frag == "":
            pass
        elif not isinstance(frag, str):
            raise AttributeError("input parameters must be strings")
        else:
            non_null_args.append(frag.strip("/"))
    joined_str = "/".join(non_null_args)
    return joined_str


def check_is_str(s) -> str:
    if isinstance(s, str):
        return s
    raise TypeError(f"A string is expected, got {s}")


def get_type(obj) -> str:
    return obj.__class__.__name__


def uuid4_str() -> str:
    return str(uuid4())


def tiny_id(n: int = 8) -> str:
    if n < 1:
        n = 8
    return uuid4().hex[0:n]


def is_uuid_v4(id: str | UUID) -> bool:
    if id is None or not isinstance(id, (str, UUID)):
        return False
    try:
        uuid4 = UUID(str(id))
        return True if uuid4.version == 4 else False
    except ValueError:
        return False


def check_is_uuid4(id: str | UUID) -> str:
    if id is None:
        raise ValueError("Input parameter should not be null")
    if not isinstance(id, (str, UUID)):
        raise ValueError(f"Input parameter is not a valid UUID v4: '{id}'")
    try:
        uuid_v4 = UUID(str(id))
        if uuid_v4.version == 4:
            return str(uuid_v4)
    except ValueError:
        pass
    raise ValueError(f"Input parameter is not a valid UUID v4: '{id}'")


def ensure_uuid4(id) -> UUID:
    try:
        uid = UUID(str(id))  # normalize
    except Exception as e:
        raise ValueError(f"Invalid UUID format: {id}") from e
    if uid.version != 4:
        raise ValueError(f"channel_id must be a UUIDv4, got v{uid.version}")
    return uid


def strip_quotes(v: Any) -> Any:
    return v[1:-1] if isinstance(v, str) and len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'") else v


def normalize_to_snake_case(s: str) -> str:
    return sub(r"[^\w]", "_", str(s).lower())


def normalize_column_name(s: str) -> str:
    # Basic normalization
    s = normalize_to_snake_case(s)
    # Optionally: collapse multiple underscores
    s = sub(r"_+", "_", s)
    # Strip leading/trailing underscores
    s = s.strip("_")

    if s[0].isdigit():
        # Prefix if starting with digit
        s = "col_" + s
    elif not s:
        # Generate 8-character random name
        s = "col_" + "".join(choices(ascii_lowercase + digits, k=8))
    return s


TimeSpec = Literal["seconds", "milliseconds", "microseconds"]


def now_iso_str(timespec: TimeSpec = "seconds") -> str:
    return datetime.now().astimezone().isoformat(timespec=timespec)


# --------------------------------------------------------------------------------------------------
# Base 64 strings
# --------------------------------------------------------------------------------------------------
def pad_b64_str(jwt_base64url: str) -> str:
    """Adds equal signs at the end of the string for its length to reach a multiple of 4"""
    jwt_str_length = len(jwt_base64url)
    _, mod = divmod(jwt_str_length, 4)
    return jwt_base64url if mod == 0 else jwt_base64url.ljust(jwt_str_length + 4 - mod, "=")


def is_base64_url(sb) -> bool:
    """
    Check if an input is urlsafe-base64 encoded
    :param sb: a string or a bytes
    source: https://stackoverflow.com/a/45928164
    """
    try:
        if isinstance(sb, str):
            # If there's any unicode here, an exception will be thrown and the function will return false
            sb_bytes = bytes(sb, "ascii")
        elif isinstance(sb, bytes):
            sb_bytes = sb
        else:
            raise ValueError("Argument must be string or bytes")
        return urlsafe_b64encode(urlsafe_b64decode(sb_bytes)) == sb_bytes
    except Exception:
        return False


def encode_b64url(s: str) -> str:
    return urlsafe_b64encode(s.encode("utf-8")).decode("utf-8")


def decode_b64url(b64_str: str) -> str:
    padded_str = pad_b64_str(b64_str)
    if not is_base64_url(padded_str):
        raise ValueError("Input string should be encoded in base64url")
    try:
        return urlsafe_b64decode(padded_str).decode("utf-8")
    except Exception as e:
        raise ValueError("Input string is not properly encoded in base64url") from e


if __name__ == "__main__":
    here = "str_utils"
    print(here, "strip_quotes 'toto':", strip_quotes("'toto'"))
    print(here, 'strip_quotes "toto":', strip_quotes('"toto"'))
