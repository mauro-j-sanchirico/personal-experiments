from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH: Path = Path(__file__).resolve().parents[2] / 'config.yaml'


def load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open(encoding='utf-8') as config_file:
        config: Any = yaml.safe_load(config_file)
    if not isinstance(config, dict):
        raise ValueError(f'Invalid config file: {_CONFIG_PATH}')
    return config
