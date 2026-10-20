import re
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, tzinfo
from json import dumps
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
            raise TypeError("input parameters must be strings")
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


def serialize_uuid(v: Any) -> Any:
    """Serialize UUID-bearing values for request/response bodies.

    Convention: UUIDs inside serialized bodies use the compact ``.hex`` form
    (no dashes); the dashed ``str(uuid)`` form is reserved for URL paths/routes
    (see :func:`check_is_uuid4`).

    This is a serializer, not a validator. A value that is already a ``str``
    (or any non-UUID, non-dict) passes through unchanged; malformed ids are
    rejected earlier, at the model's ``id`` validator.
    """
    if isinstance(v, UUID):
        return v.hex
    if isinstance(v, dict):
        return {k: serialize_uuid(val) for k, val in v.items()}
    return v


def serialize(x: Any, *, exclude_none: bool = True) -> Any:
    if isinstance(x, (bool, int, float)):
        return x
    if isinstance(x, UUID):
        return x.hex
    if exclude_none and not x and isinstance(x, (list, dict, set, tuple, str)):
        return None
    if isinstance(x, (list, tuple, set)):
        if (tx := type(x)) is set:
            tx = list
        return tx(sv for val in x if not ((sv := serialize(val)) is None and exclude_none))
    if isinstance(x, dict):
        return {key: sv for key, val in x.items() if not ((sv := serialize(val)) is None and exclude_none)}
    if hasattr(x, "model_dump"):
        return x.model_dump(exclude_none=exclude_none)
    return x


def validate_orcid(v: str) -> str:
    v = v.strip()
    # Match optional https://, optional http://, then orcid.org/, then the 4-digit groups
    match = re.fullmatch(r"(?:https?://)?(?:orcid\.org/)?((\d{4}-){3}\d{4})", v)
    if not match:
        raise ValueError("not a valid ORCID")
    # Return only the 4 quadruplets
    return match[1]


def tiny_id(n: int = 8) -> str:
    if n < 1:
        n = 8
    return uuid4().hex[0:n]


def is_uuid_v4(id: str | UUID) -> bool:
    if id is None or not isinstance(id, (str, UUID)):
        return False
    try:
        return UUID(str(id)).version == 4
    except Exception:
        return False


def check_is_uuid4(id: str | UUID | None) -> str:
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
        raise ValueError(f"Expected UUID v4, got UUID v{uid.version}")
    return uid


def strip_quotes(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


SQL_COL_MAX_LEN = 63


def split_strip(s: str | None = None, sep: str = ",", norm=None) -> list[str]:
    """Split on sep, strip whitespace, and optionally normalize each part."""
    if s is None:
        return []
    parts = [p.strip() for p in s.split(sep)]
    if norm:
        return [n for n in (norm(p) for p in parts) if n not in (None, "")]
    return [p for p in parts if p]


def normalize_name(
    s: str,
    *,
    keep_dots: bool = False,
    prefix: str = "",
) -> str:
    """Normalize a column name the same way kronicle's server does.

    Raises ValueError for empty/invalid names. Dots are preserved when
    keep_dots is True (used by `col`/`any` dotted filters).
    """
    if s is None:
        raise ValueError("A name should be provided")
    if not isinstance(s, str):
        raise TypeError(f"Name should be a string, got {get_type(s)}")
    if not s:
        raise ValueError("Name cannot be empty")
    try:
        if keep_dots:
            parts = split_strip(s, ".", normalize_name)
            normed = ".".join(p for p in parts if p)
        else:
            normed = normalize_to_snake_case(s)
        normed = sub(r"_+", "_", normed)
        normed = normed.strip("_")
        if len(normed) < 1:
            raise ValueError("Name is invalid")
        if normed[0].isdigit():
            if not prefix:
                raise ValueError("Name is invalid")
            normed = prefix + normed
        return normed[:SQL_COL_MAX_LEN]
    except Exception as exc:
        raise ValueError("Name is invalid") from exc


def normalize_name_keep_dots(s: str, *, prefix: str = "") -> str:
    return normalize_name(s, keep_dots=True, prefix=prefix)


def normalize_sort_name(s: str, *, prefix: str = "") -> str:
    s = s.strip()
    if not s:
        raise ValueError("Sort field cannot be empty")
    if s[0] == "-":
        normed = normalize_name(s[1:], prefix=prefix)
        return f"-{normed}" if normed else ""
    return normalize_name(s, prefix=prefix)


def normalize_to_snake_case(s: str) -> str:
    return sub(r"[^\w]", "_", str(s).lower())


def normalize_column_name(s: str) -> str:
    if not s:
        # Generate 8-character random name
        return "col_" + "".join(choices(ascii_lowercase + digits, k=8))  # not used for security # nosec B311
    # Basic normalization
    s = normalize_to_snake_case(s)
    # Optionally: collapse multiple underscores
    s = sub(r"_+", "_", s)
    # Strip leading/trailing underscores
    s = s.strip("_")
    if len(s) < 1:
        raise ValueError("Name is invalid")
    if s[0].isdigit():
        # Prefix if starting with digit
        s = "col_" + s
    return s


TimeSpec = Literal["seconds", "milliseconds", "microseconds"]


def now_iso_str(timespec: TimeSpec = "seconds") -> str:
    return datetime.now().astimezone().isoformat(timespec=timespec)


def now_ms(tz: tzinfo | None = None) -> str:
    return datetime.now(tz).isoformat(sep=" ", timespec="milliseconds")


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


def param_dict_to_str(params: dict | None = None) -> str:
    if not params:
        return ""
    return "?" + ("&".join([f"{k}={v}" for k, v in params.items()]))


if __name__ == "__main__":  # pragma: no cover
    here = "str_utils"
    print(here, "strip_quotes 'toto':", strip_quotes("'toto'"))
    print(here, 'strip_quotes "toto":', strip_quotes('"toto"'))
    ll = [u := uuid4(), {}, [], "", False, True]
    s = {u, "", False, True, 42}
    t = (u, {}, [], "", False, True, ll)
    d = {
        "uuid": u,
        "dict": {},
        "list": [],
        "ll": ll,
        "set": s,
        "tuple": t,
        "str": "",
        "false": False,
        "true": True,
    }
    print(here, "serialize bool", serialize(False))
    print(here, "serialize int", serialize(0))
    print(here, "serialize float", serialize(0.0))
    print(here, "serialize list", serialize([True, False, 0, 0.0]))
    print(here, "serialize list", serialize(ll))
    print(here, "serialize list", serialize(ll, exclude_none=False))
    print(here, "serialize set", serialize(s))
    print(here, "serialize tuple", serialize(t))
    print(here, "serialize dict", serialize(d))
    print(here, "serialize dict", dumps(serialize(d, exclude_none=False)))

    for e in ["z", 1, 1.2, True, Any, type, (), [], {}]:
        print(here, "get_type", e, "->", get_type(e))
