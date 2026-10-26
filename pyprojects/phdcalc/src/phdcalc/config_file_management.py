"""Load YAML configuration from the project's source checkout."""

from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH: Path = Path(__file__).resolve().parents[2] / 'config.yaml'


def load_config() -> dict[str, Any]:
    """Load config.yaml as a dictionary, rejecting a non-mapping root value."""
    with _CONFIG_PATH.open(encoding='utf-8') as config_file:
        config: Any = yaml.safe_load(config_file)
    if not isinstance(config, dict):
        raise ValueError(f'Invalid config file: {_CONFIG_PATH}')
    return config
