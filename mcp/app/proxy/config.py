"""
Configuration management for MCP Proxy Engine.

This module handles loading, validating, and managing configuration
for external MCP server connections and proxy settings.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ServerSettings:
    """Settings for individual MCP server connections."""

    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5
    tool_prefix: str = ""
    health_check_interval: int = 60

    def __post_init__(self):
        """Validate settings after initialization."""
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts must be non-negative")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")
        if self.health_check_interval <= 0:
            raise ValueError("health_check_interval must be positive")


@dataclass
class ServerConfig:
    """Configuration for a single MCP server."""

    name: str
    enabled: bool
    description: str
    type: str
    settings: ServerSettings

    # Connection-specific fields
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """Validate server configuration after initialization."""
        if not self.name:
            raise ValueError("Server name cannot be empty")

        if self.type not in ["stdio", "sse", "streamable-http", "websocket", "tcp"]:
            raise ValueError(f"Unsupported server type: {self.type}")

        # Validate type-specific requirements
        if self.type == "stdio":
            if not self.command:
                raise ValueError("stdio servers require a command")
        elif self.type in ["sse", "streamable-http", "websocket"]:
            if not self.url:
                raise ValueError(f"{self.type} servers require a url")

        # Set defaults
        if self.args is None:
            self.args = []
        if self.env is None:
            self.env = {}
        if self.headers is None:
            self.headers = {}

    @property
    def is_network_based(self) -> bool:
        """Check if this server uses network connections."""
        return self.type in ["sse", "streamable-http", "websocket", "tcp"]

    @property
    def is_process_based(self) -> bool:
        """Check if this server uses process connections."""
        return self.type == "stdio"

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for this server."""
        if self.is_process_based:
            return {"command": self.command, "args": self.args, "env": self.env}
        elif self.is_network_based:
            return {"url": self.url, "headers": self.headers}
        else:
            return {}


@dataclass
class GlobalSettings:
    """Global settings for the proxy engine."""

    discovery_interval: int = 300
    health_check_interval: int = 60
    max_concurrent_calls: int = 10
    enable_timeline_logging: bool = True
    log_level: str = "INFO"

    def __post_init__(self):
        """Validate global settings after initialization."""
        if self.discovery_interval <= 0:
            raise ValueError("discovery_interval must be positive")
        if self.health_check_interval <= 0:
            raise ValueError("health_check_interval must be positive")
        if self.max_concurrent_calls <= 0:
            raise ValueError("max_concurrent_calls must be positive")
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {self.log_level}")


class ProxyConfig:
    """
    Main configuration class for MCP Proxy Engine.

    Handles loading, validation, and access to proxy configuration.
    """

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialize proxy configuration.

        Args:
            config_path: Path to configuration file. If None, uses default location.
        """
        self.config_path = self._resolve_config_path(config_path)
        self.version: str = "1.0"
        self.servers: Dict[str, ServerConfig] = {}
        self.global_settings: GlobalSettings = GlobalSettings()
        self._loaded = False

    def _resolve_config_path(self, config_path: Optional[Union[str, Path]]) -> Path:
        """Resolve the configuration file path."""
        if config_path:
            return Path(config_path)

        # Default to mcp-proxy.json in the same directory as this module
        module_dir = Path(__file__).parent.parent.parent
        return module_dir / "mcp-proxy.json"

    def load(self) -> None:
        """
        Load configuration from file.

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
            json.JSONDecodeError: If config file is not valid JSON
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        logger.info(f"Loading MCP proxy configuration from {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")

        self._validate_and_load_config(config_data)
        self._loaded = True

        logger.info(f"Loaded configuration for {len(self.servers)} servers")

    def _validate_and_load_config(self, config_data: Dict[str, Any]) -> None:
        """Validate and load configuration data."""
        # Validate version
        self.version = config_data.get("version", "1.0")
        if self.version != "1.0":
            logger.warning(f"Unknown configuration version: {self.version}")

        # Load global settings
        global_settings_data = config_data.get("global_settings", {})
        self.global_settings = GlobalSettings(**global_settings_data)

        # Load server configurations
        servers_data = config_data.get("mcpServers", {})
        if not isinstance(servers_data, dict):
            raise ValueError("mcpServers must be a dictionary")

        self.servers = {}
        for server_name, server_data in servers_data.items():
            try:
                # Extract settings
                settings_data = server_data.get("settings", {})
                settings = ServerSettings(**settings_data)

                # Create server config
                server_config = ServerConfig(
                    name=server_name,
                    enabled=server_data.get("enabled", False),
                    description=server_data.get("description", ""),
                    type=server_data.get("type", "stdio"),
                    settings=settings,
                    command=server_data.get("command"),
                    args=server_data.get("args"),
                    env=server_data.get("env"),
                    url=server_data.get("url"),
                    headers=server_data.get("headers"),
                )

                self.servers[server_name] = server_config
                logger.debug(
                    f"Loaded server config: {server_name} ({server_config.type})"
                )

            except Exception as e:
                logger.error(f"Failed to load server config '{server_name}': {e}")
                raise ValueError(f"Invalid server configuration '{server_name}': {e}")

    def reload(self) -> None:
        """Reload configuration from file."""
        logger.info("Reloading MCP proxy configuration")
        self.load()

    def save(self) -> None:
        """Save current configuration to file."""
        config_data = self.to_dict()

        logger.info(f"Saving MCP proxy configuration to {self.config_path}")

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        servers_data = {}
        for name, server in self.servers.items():
            server_data = {
                "enabled": server.enabled,
                "description": server.description,
                "type": server.type,
                "settings": {
                    "timeout": server.settings.timeout,
                    "retry_attempts": server.settings.retry_attempts,
                    "retry_delay": server.settings.retry_delay,
                    "tool_prefix": server.settings.tool_prefix,
                    "health_check_interval": server.settings.health_check_interval,
                },
            }

            # Add connection-specific fields
            if server.command is not None:
                server_data["command"] = server.command
            if server.args:
                server_data["args"] = server.args
            if server.env:
                server_data["env"] = server.env
            if server.url is not None:
                server_data["url"] = server.url
            if server.headers:
                server_data["headers"] = server.headers

            servers_data[name] = server_data

        return {
            "version": self.version,
            "mcpServers": servers_data,
            "global_settings": {
                "discovery_interval": self.global_settings.discovery_interval,
                "health_check_interval": self.global_settings.health_check_interval,
                "max_concurrent_calls": self.global_settings.max_concurrent_calls,
                "enable_timeline_logging": self.global_settings.enable_timeline_logging,
                "log_level": self.global_settings.log_level,
            },
        }

    def get_enabled_servers(self) -> List[ServerConfig]:
        """Get list of enabled server configurations."""
        return [server for server in self.servers.values() if server.enabled]

    def get_server(self, name: str) -> Optional[ServerConfig]:
        """Get server configuration by name."""
        return self.servers.get(name)

    def add_server(self, server_config: ServerConfig) -> None:
        """Add a new server configuration."""
        if server_config.name in self.servers:
            raise ValueError(f"Server '{server_config.name}' already exists")

        self.servers[server_config.name] = server_config
        logger.info(f"Added server configuration: {server_config.name}")

    def remove_server(self, name: str) -> bool:
        """Remove a server configuration."""
        if name in self.servers:
            del self.servers[name]
            logger.info(f"Removed server configuration: {name}")
            return True
        return False

    def update_server(self, name: str, **kwargs) -> bool:
        """Update server configuration."""
        if name not in self.servers:
            return False

        server = self.servers[name]
        for key, value in kwargs.items():
            if hasattr(server, key):
                setattr(server, key, value)
            elif hasattr(server.settings, key):
                setattr(server.settings, key, value)

        logger.info(f"Updated server configuration: {name}")
        return True

    def validate(self) -> List[str]:
        """
        Validate the current configuration.

        Returns:
            List of validation error messages. Empty list if valid.
        """
        errors = []

        try:
            # Validate global settings
            GlobalSettings(**self.global_settings.__dict__)
        except Exception as e:
            errors.append(f"Invalid global settings: {e}")

        # Validate each server
        for name, server in self.servers.items():
            try:
                # Re-validate server config
                ServerConfig(**server.__dict__)
            except Exception as e:
                errors.append(f"Invalid server '{name}': {e}")

        # Check for duplicate tool prefixes among enabled servers
        enabled_servers = self.get_enabled_servers()
        prefixes = [
            s.settings.tool_prefix for s in enabled_servers if s.settings.tool_prefix
        ]
        if len(prefixes) != len(set(prefixes)):
            errors.append("Duplicate tool prefixes found among enabled servers")

        return errors

    @property
    def is_loaded(self) -> bool:
        """Check if configuration has been loaded."""
        return self._loaded

    def __str__(self) -> str:
        """String representation of configuration."""
        enabled_count = len(self.get_enabled_servers())
        total_count = len(self.servers)
        return f"ProxyConfig(servers={enabled_count}/{total_count} enabled, version={self.version})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"ProxyConfig(config_path={self.config_path}, "
            f"servers={list(self.servers.keys())}, "
            f"version={self.version})"
        )


# Convenience function for loading configuration
def load_proxy_config(config_path: Optional[Union[str, Path]] = None) -> ProxyConfig:
    """
    Load proxy configuration from file.

    Args:
        config_path: Path to configuration file. If None, uses default location.

    Returns:
        Loaded ProxyConfig instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    config = ProxyConfig(config_path)
    config.load()
    return config
