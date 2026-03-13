from configparser import ConfigParser, ExtendedInterpolation
from os import environ
from pathlib import Path

from kronicle_sdk.utils.file_utils import check_is_file


def read_ini_conf(file_path) -> ConfigParser:
    check_is_file(file_path)
    config_reader = ConfigParser(interpolation=ExtendedInterpolation())
    config_reader.read(file_path)
    return config_reader


def parse_value(value: str):
    """Simple type inference for env values."""
    value = value.strip()
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    # strip quotes if present
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def load_env(file_path: str = ".env", override: bool = False):
    env_path = Path(file_path)
    env_vars = {}
    if not env_path.exists():
        return env_vars

    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            if key.startswith("export "):
                key = key[7:]
            key = key.strip()
            value = value.strip()
            typed_value = parse_value(value)
            env_vars[key] = typed_value
            if override or key not in environ:
                environ[key] = str(typed_value)  # os.environ must stay str
    return env_vars
