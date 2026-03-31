from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional, Union
import configparser

PathLike = Union[str, Path]


def load_ini_template(template_path: PathLike) -> configparser.ConfigParser:
    template_path = Path(template_path)
    if not template_path.exists():
        raise FileNotFoundError(f"INI template not found: {template_path}")

    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(template_path)
    return config


def _ensure_section(config: configparser.ConfigParser, section: str) -> None:
    if not config.has_section(section):
        config.add_section(section)



def apply_overrides(
    config: configparser.ConfigParser,
    overrides: Mapping[str, Mapping[str, object]],
) -> configparser.ConfigParser:
    for section, values in overrides.items():
        _ensure_section(config, section)
        for key, value in values.items():
            config.set(section, key, str(value))
    return config



def prepare_helios_config(
    template_path: PathLike,
    output_path: PathLike,
    field_obj_path: Optional[PathLike] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    utc_offset: Optional[int] = None,
    additional_overrides: Optional[Mapping[str, Mapping[str, object]]] = None,
) -> Path:
    """
    Write a run-specific Helios config.

    Confirmed keys used by the user's current parallel.cpp:
      [Paths]    fieldfilepath
      [Location] latitude / longitude / utc_offset
    """
    config = load_ini_template(template_path)

    overrides: dict[str, dict[str, object]] = {}

    if field_obj_path is not None:
        overrides.setdefault("Paths", {})["fieldfilepath"] = str(Path(field_obj_path).resolve())

    if latitude is not None:
        overrides.setdefault("Location", {})["latitude"] = latitude
    if longitude is not None:
        overrides.setdefault("Location", {})["longitude"] = longitude
    if utc_offset is not None:
        overrides.setdefault("Location", {})["utc_offset"] = utc_offset

    if overrides:
        apply_overrides(config, overrides)
    if additional_overrides:
        apply_overrides(config, additional_overrides)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        config.write(f)
    return output_path
