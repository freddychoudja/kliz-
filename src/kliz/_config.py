"""Settings file support for the kliz CLI."""

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on Python 3.10 only
    import tomli as tomllib

# Setting name -> accepted value types. Names match the long CLI options.
SETTINGS: dict[str, tuple[type, ...]] = {
    "indexnow_api_key": (str,),
    "indexnow_key_location": (str,),
    "google_service_account_file": (str,),
    "gsc_site": (str,),
    "gsc_sitemap": (str,),
    "gsc_service_account_file": (str,),
    "sitemap": (str,),
    "max_attempts": (int,),
    "timeout": (int, float),
    "allow_query": (bool,),
}


_TYPE_NAMES = {str: "string", int: "integer", float: "number", bool: "boolean"}


class ConfigurationError(ValueError):
    """Raised when the CLI is misconfigured."""


def find_config(explicit: str | None, directory: Path) -> Path | None:
    """Return the settings file to use, or ``None``.

    An explicit ``--config`` path must exist; otherwise ``kliz.toml`` and then
    ``pyproject.toml`` are looked up in *directory*.
    """

    if explicit is not None:
        path = Path(explicit)
        if not path.is_file():
            raise ConfigurationError(f"config file not found: {explicit}")
        return path
    for name in ("kliz.toml", "pyproject.toml"):
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def load_config(path: Path) -> dict[str, Any]:
    """Read kliz settings from *path*.

    ``pyproject.toml`` holds them under ``[tool.kliz]``; any other file holds
    them at the top level. Keys may use dashes or underscores.
    """

    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError(f"cannot read {path}: {exc}") from exc

    if path.name == "pyproject.toml":
        section = data.get("tool", {}).get("kliz", {})
        where = f"{path} [tool.kliz]"
    else:
        section = data
        where = str(path)
    if not isinstance(section, Mapping):
        raise ConfigurationError(f"{where} must be a table of settings")
    return _validate(section, where)


def _validate(section: Mapping[str, Any], where: str) -> dict[str, Any]:
    settings: dict[str, Any] = {}
    for raw_key, value in section.items():
        key = raw_key.replace("-", "_")
        if key not in SETTINGS:
            known = ", ".join(name.replace("_", "-") for name in SETTINGS)
            raise ConfigurationError(
                f"{where}: unknown setting {raw_key!r} (known: {known})"
            )
        types = SETTINGS[key]
        if isinstance(value, bool) and bool not in types:
            valid = False
        else:
            valid = isinstance(value, types)
        if not valid:
            expected = " or ".join(_TYPE_NAMES[t] for t in types)
            article = "an" if expected[0] in "aeiou" else "a"
            raise ConfigurationError(f"{where}: {raw_key} must be {article} {expected}")
        settings[key] = value
    return settings
