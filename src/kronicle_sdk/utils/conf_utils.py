from configparser import ConfigParser, ExtendedInterpolation, NoOptionError, NoSectionError
from os import environ, getenv
from pathlib import Path
from typing import Any

from kronicle_sdk.conf.env_keys import KRONICLE_SDK_CONF
from kronicle_sdk.utils.file_utils import check_is_file, is_file


def read_conf_file():
    ini_file = getenv(KRONICLE_SDK_CONF, "./conf/config.ini")
    if ini_file and is_file(ini_file):
        return read_ini_conf(ini_file)


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


def get_setting(
    *,
    env: str | None = None,
    conf: ConfigParser | None = None,
    section: str | None = None,
    param: str | None = None,
    default: Any | None = None,
):
    """
    Retrieve a setting from an environment variable or, alternatively, an ini file.
    If both are set, values from ENV are preferred.
    """
    if env:
        env_val = getenv(env.upper())
        if env_val is not None:
            # logger(here, "Extracted from environment variables:", env)
            return env_val
    if conf and section and param:
        try:
            conf_val = conf.get(section.lower(), param.lower())
        except NoSectionError as e:
            if default is None:
                raise RuntimeError(f"Missing config section '{section}'") from e
            return default
        except NoOptionError as e:
            if default is None:
                raise RuntimeError(f"Missing '{param}' in config section '{section}'") from e
            return default
        if conf_val:
            return conf_val
    return default
