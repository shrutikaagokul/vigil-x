"""
Abstract base rule for all Vigil-X detection rules.

Every rule (R01–R10) must subclass BaseRule and implement detect().
This ensures uniform interface across the entire rule subsystem.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml

from vigilx.models.alert import Alert


# Resolve config path relative to this file's location
_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "config"


def load_rules_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    Load the rules configuration YAML.

    Parameters
    ----------
    config_path : Path, optional
        Override path to the config file. Defaults to config/rules_config.yaml.
    """
    if config_path is None:
        config_path = _CONFIG_DIR / "rules_config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


class BaseRule(ABC):
    """
    Abstract base class for Vigil-X detection rules.

    Subclasses must implement:
        - detect(data) -> list[Alert]

    The base class handles:
        - Loading rule-specific config from rules_config.yaml
        - Providing rule_id and rule_version
        - Checking the enabled flag
    """

    rule_id: str = ""
    rule_version: str = "1.0"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Initialize with optional config override.

        Parameters
        ----------
        config : dict, optional
            Full rules config dict. If None, loads from default YAML.
        """
        if config is None:
            config = load_rules_config()

        all_rules_cfg = config.get("rules", config)
        self.cfg = all_rules_cfg.get(self.rule_id, {})
        self.rule_version = self.cfg.get("version", self.rule_version)
        self.enabled = self.cfg.get("enabled", True)

    @abstractmethod
    def detect(self, data: dict[str, Any]) -> list[Alert]:
        """
        Run detection logic and return standardized alerts.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary of DataFrames keyed by table name
            (e.g., "claims", "members", "providers", "facilities", etc.)

        Returns
        -------
        list[Alert]
            Zero or more alerts with auditable evidence.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} rule_id={self.rule_id} v{self.rule_version}>"
