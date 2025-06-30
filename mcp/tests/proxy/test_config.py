"""
Tests for MCP Proxy configuration management.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.proxy.config import (
    ProxyConfig,
    ServerConfig,
    ServerSettings,
    GlobalSettings,
    load_proxy_config,
)


class TestServerSettings:
    """Test ServerSettings dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        settings = ServerSettings()
        assert settings.timeout == 30
        assert settings.retry_attempts == 3
        assert settings.retry_delay == 5
        assert settings.tool_prefix == ""
        assert settings.health_check_interval == 60

    def test_custom_values(self):
        """Test custom values are set correctly."""
        settings = ServerSettings(
            timeout=60,
            retry_attempts=5,
            retry_delay=10,
            tool_prefix="test_",
            health_check_interval=120,
        )
        assert settings.timeout == 60
        assert settings.retry_attempts == 5
        assert settings.retry_delay == 10
        assert settings.tool_prefix == "test_"
        assert settings.health_check_interval == 120

    def test_validation_errors(self):
        """Test validation errors for invalid values."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ServerSettings(timeout=0)

        with pytest.raises(ValueError, match="retry_attempts must be non-negative"):
            ServerSettings(retry_attempts=-1)

        with pytest.raises(ValueError, match="retry_delay must be non-negative"):
            ServerSettings(retry_delay=-1)

        with pytest.raises(ValueError, match="health_check_interval must be positive"):
            ServerSettings(health_check_interval=0)


class TestServerConfig:
    """Test ServerConfig dataclass."""

    def test_stdio_server_config(self):
        """Test stdio server configuration."""
        settings = ServerSettings()
        config = ServerConfig(
            name="test-stdio",
            enabled=True,
            description="Test stdio server",
            type="stdio",
            settings=settings,
            command="/path/to/server",
            args=["--arg1", "value1"],
            env={"VAR": "value"},
        )

        assert config.name == "test-stdio"
        assert config.enabled is True
        assert config.type == "stdio"
        assert config.command == "/path/to/server"
        assert config.args == ["--arg1", "value1"]
        assert config.env == {"VAR": "value"}
        assert config.is_process_based is True
        assert config.is_network_based is False

    def test_sse_server_config(self):
        """Test SSE server configuration."""
        settings = ServerSettings()
        config = ServerConfig(
            name="test-sse",
            enabled=True,
            description="Test SSE server",
            type="sse",
            settings=settings,
            url="http://localhost:3000/sse",
            headers={"Authorization": "Bearer token"},
        )

        assert config.name == "test-sse"
        assert config.type == "sse"
        assert config.url == "http://localhost:3000/sse"
        assert config.headers == {"Authorization": "Bearer token"}
        assert config.is_process_based is False
        assert config.is_network_based is True

    def test_validation_errors(self):
        """Test validation errors."""
        settings = ServerSettings()

        # Empty name
        with pytest.raises(ValueError, match="Server name cannot be empty"):
            ServerConfig(
                name="", enabled=True, description="", type="stdio", settings=settings
            )

        # Invalid type
        with pytest.raises(ValueError, match="Unsupported server type"):
            ServerConfig(
                name="test",
                enabled=True,
                description="",
                type="invalid",
                settings=settings,
            )

        # stdio without command
        with pytest.raises(ValueError, match="stdio servers require a command"):
            ServerConfig(
                name="test",
                enabled=True,
                description="",
                type="stdio",
                settings=settings,
            )

        # sse without url
        with pytest.raises(ValueError, match="sse servers require a url"):
            ServerConfig(
                name="test", enabled=True, description="", type="sse", settings=settings
            )

    def test_get_connection_info(self):
        """Test connection info extraction."""
        settings = ServerSettings()

        # stdio server
        stdio_config = ServerConfig(
            name="stdio-test",
            enabled=True,
            description="",
            type="stdio",
            settings=settings,
            command="/path/to/server",
            args=["--arg"],
            env={"VAR": "value"},
        )

        stdio_info = stdio_config.get_connection_info()
        assert stdio_info == {
            "command": "/path/to/server",
            "args": ["--arg"],
            "env": {"VAR": "value"},
        }

        # sse server
        sse_config = ServerConfig(
            name="sse-test",
            enabled=True,
            description="",
            type="sse",
            settings=settings,
            url="http://localhost:3000",
            headers={"Auth": "token"},
        )

        sse_info = sse_config.get_connection_info()
        assert sse_info == {
            "url": "http://localhost:3000",
            "headers": {"Auth": "token"},
        }


class TestGlobalSettings:
    """Test GlobalSettings dataclass."""

    def test_default_values(self):
        """Test default values."""
        settings = GlobalSettings()
        assert settings.discovery_interval == 300
        assert settings.health_check_interval == 60
        assert settings.max_concurrent_calls == 10
        assert settings.enable_timeline_logging is True
        assert settings.log_level == "INFO"

    def test_validation_errors(self):
        """Test validation errors."""
        with pytest.raises(ValueError, match="discovery_interval must be positive"):
            GlobalSettings(discovery_interval=0)

        with pytest.raises(ValueError, match="health_check_interval must be positive"):
            GlobalSettings(health_check_interval=0)

        with pytest.raises(ValueError, match="max_concurrent_calls must be positive"):
            GlobalSettings(max_concurrent_calls=0)

        with pytest.raises(ValueError, match="Invalid log level"):
            GlobalSettings(log_level="INVALID")


class TestProxyConfig:
    """Test ProxyConfig class."""

    @pytest.fixture
    def sample_config_data(self):
        """Sample configuration data."""
        return {
            "version": "1.0",
            "mcpServers": {
                "test-server": {
                    "enabled": True,
                    "description": "Test server",
                    "type": "stdio",
                    "command": "/path/to/server",
                    "args": ["--test"],
                    "env": {"TEST": "value"},
                    "settings": {
                        "timeout": 45,
                        "retry_attempts": 2,
                        "retry_delay": 3,
                        "tool_prefix": "test_",
                        "health_check_interval": 30,
                    },
                }
            },
            "global_settings": {
                "discovery_interval": 600,
                "health_check_interval": 120,
                "max_concurrent_calls": 5,
                "enable_timeline_logging": False,
                "log_level": "DEBUG",
            },
        }

    @pytest.fixture
    def temp_config_file(self, sample_config_data):
        """Create a temporary config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_config_data, f)
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_load_config(self, temp_config_file):
        """Test loading configuration from file."""
        config = ProxyConfig(temp_config_file)
        config.load()

        assert config.is_loaded is True
        assert config.version == "1.0"
        assert len(config.servers) == 1

        server = config.get_server("test-server")
        assert server is not None
        assert server.enabled is True
        assert server.type == "stdio"
        assert server.command == "/path/to/server"
        assert server.settings.timeout == 45
        assert server.settings.tool_prefix == "test_"

        assert config.global_settings.discovery_interval == 600
        assert config.global_settings.log_level == "DEBUG"

    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises error."""
        config = ProxyConfig("/nonexistent/path.json")

        with pytest.raises(FileNotFoundError):
            config.load()

    def test_load_invalid_json(self):
        """Test loading invalid JSON raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_path = Path(f.name)

        try:
            config = ProxyConfig(temp_path)
            with pytest.raises(ValueError, match="Invalid JSON"):
                config.load()
        finally:
            temp_path.unlink()

    def test_get_enabled_servers(self, temp_config_file):
        """Test getting enabled servers."""
        config = ProxyConfig(temp_config_file)
        config.load()

        enabled = config.get_enabled_servers()
        assert len(enabled) == 1
        assert enabled[0].name == "test-server"

    def test_add_remove_server(self):
        """Test adding and removing servers."""
        config = ProxyConfig()
        settings = ServerSettings()

        server = ServerConfig(
            name="new-server",
            enabled=True,
            description="New server",
            type="stdio",
            settings=settings,
            command="/path/to/new",
        )

        # Add server
        config.add_server(server)
        assert "new-server" in config.servers

        # Try to add duplicate
        with pytest.raises(ValueError, match="already exists"):
            config.add_server(server)

        # Remove server
        assert config.remove_server("new-server") is True
        assert "new-server" not in config.servers

        # Remove non-existent
        assert config.remove_server("nonexistent") is False

    def test_save_and_load_roundtrip(self, sample_config_data):
        """Test saving and loading configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Create config and load data
            config = ProxyConfig(temp_path)
            config._validate_and_load_config(sample_config_data)

            # Save to file
            config.save()

            # Load from file
            config2 = ProxyConfig(temp_path)
            config2.load()

            # Verify data matches
            assert config2.version == config.version
            assert len(config2.servers) == len(config.servers)

            server1 = config.get_server("test-server")
            server2 = config2.get_server("test-server")
            assert server1.name == server2.name
            assert server1.enabled == server2.enabled
            assert server1.settings.timeout == server2.settings.timeout

        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_validate_config(self, temp_config_file):
        """Test configuration validation."""
        config = ProxyConfig(temp_config_file)
        config.load()

        # Valid config should have no errors
        errors = config.validate()
        assert len(errors) == 0

    def test_convenience_function(self, temp_config_file):
        """Test convenience function for loading config."""
        config = load_proxy_config(temp_config_file)

        assert config.is_loaded is True
        assert len(config.servers) == 1
