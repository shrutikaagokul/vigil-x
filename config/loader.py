"""
Configuration loader for Vigil-X.

Reads rules_config.yaml and provides typed access to rule thresholds.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

_CONFIG_CACHE: Optional[Dict[str, Any]] = None
_DEFAULT_CONFIG_PATH = Path(__file__).parent / "rules_config.yaml"


def load_config(path: Optional[str] = None, force_reload: bool = False) -> Dict[str, Any]:
    """Load the YAML config file. Caches after first load."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None and not force_reload:
        return _CONFIG_CACHE

    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        _CONFIG_CACHE = yaml.safe_load(f)
    return _CONFIG_CACHE


def get_rule_config(rule_id: str, path: Optional[str] = None) -> Dict[str, Any]:
    """Get configuration for a specific rule (e.g., 'R06')."""
    cfg = load_config(path)
    rule_cfg = cfg.get(rule_id)
    if rule_cfg is None:
        raise KeyError(f"No config found for rule '{rule_id}'")
    return rule_cfg


def reset_config_cache():
    """Clear config cache (for testing)."""
    global _CONFIG_CACHE
    _CONFIG_CACHE = None
