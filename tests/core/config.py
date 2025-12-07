"""
Configuration loader and manager.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from tests.core.exceptions import ConfigurationError


class ConfigManager:
    """Manages test framework configuration"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "tests/config.yaml"
        self._config: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            config_file = Path(self.config_path)

            if not config_file.exists():
                raise ConfigurationError(
                    f"Configuration file not found: {self.config_path}"
                )

            with open(config_file, "r") as f:
                self._config = yaml.safe_load(f)

            self._validate_config()
            return self._config

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in config file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def _validate_config(self) -> None:
        """Validate required configuration sections exist"""
        required_sections = ["execution", "storage"]

        for section in required_sections:
            if section not in self._config:
                raise ConfigurationError(
                    f"Missing required configuration section: {section}"
                )

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key"""
        if self._config is None:
            self.load()

        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_execution_config(self, mode: str) -> Dict[str, Any]:
        """Get execution configuration for specific mode"""
        config = self.get(f"execution.modes.{mode}")

        if config is None:
            raise ConfigurationError(f"No configuration found for mode: {mode}")

        if not config.get("enabled", False):
            raise ConfigurationError(f"Mode '{mode}' is not enabled in config")

        return config

    def get_adapter_config(self) -> Dict[str, Any]:
        """Get agent adapter configuration"""
        return self.get("adapter", {})

    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration"""
        return self.get("storage", {})

    def get_reporting_config(self) -> Dict[str, Any]:
        """Get reporting configuration"""
        return self.get("reporting", {})


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to load configuration"""
    manager = ConfigManager(config_path)
    return manager.load()
