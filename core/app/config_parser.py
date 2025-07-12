"""
Enhanced configuration parsing for database connection strings.

This module provides support for parsing various connection string formats
and converting them to standardized configuration dictionaries.
"""

import re
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs


class DatabaseConfigParser:
    """
    Parses database configuration from various formats including connection strings.
    """
    
    @staticmethod
    def parse_connection_string(connection_string: str) -> Dict[str, Any]:
        """
        Parse a database connection string into a configuration dictionary.
        
        Supports formats like:
        - postgresql://user:password@host:port/database?param=value
        - mysql://user:password@host:port/database?param=value
        - sqlite:///path/to/database.db
        - sqlite:///:memory:
        
        Args:
            connection_string: Database connection string
            
        Returns:
            Dictionary with parsed configuration
            
        Raises:
            ValueError: If connection string format is invalid
        """
        if not connection_string:
            raise ValueError("Connection string cannot be empty")
        
        try:
            parsed = urlparse(connection_string)
        except Exception as e:
            raise ValueError(f"Invalid connection string format: {e}")
        
        if not parsed.scheme:
            raise ValueError("Connection string must include a scheme (e.g., postgresql://)")
        
        # Determine database type from scheme
        scheme_mapping = {
            "sqlite": "sqlite",
            "postgresql": "postgresql",
            "postgres": "postgresql",  # Alternative scheme
            "mysql": "mysql",
            "mysql+pymysql": "mysql",
            "mysql+mysqldb": "mysql",
            "mysql+mysqlconnector": "mysql",
        }
        
        db_type = scheme_mapping.get(parsed.scheme)
        if not db_type:
            raise ValueError(f"Unsupported database scheme: {parsed.scheme}")
        
        config = {
            "type": db_type,
            "url": connection_string
        }
        
        # Parse components for non-SQLite databases
        if db_type != "sqlite":
            if parsed.hostname:
                config["host"] = parsed.hostname
            
            if parsed.port:
                config["port"] = str(parsed.port)
            
            if parsed.username:
                config["user"] = parsed.username
            
            if parsed.password:
                config["password"] = parsed.password
            
            # Database name from path (remove leading slash)
            if parsed.path and parsed.path != "/":
                config["name"] = parsed.path.lstrip("/")
            
            # Parse query parameters
            if parsed.query:
                query_params = parse_qs(parsed.query)
                
                # Extract common parameters
                for param, values in query_params.items():
                    if values:  # Take first value if multiple
                        value = values[0]
                        
                        if param in ["sslmode", "ssl_mode"]:
                            config["ssl_mode"] = value
                        elif param == "application_name":
                            config["application_name"] = value
                        elif param == "connect_timeout":
                            try:
                                config["connect_timeout"] = int(value)
                            except ValueError:
                                logging.warning(f"Invalid connect_timeout value: {value}")
                        elif param == "charset":
                            config["charset"] = value
                        elif param == "autocommit":
                            config["autocommit"] = value.lower() in ("true", "1", "yes")
        
        return config
    
    @staticmethod
    def build_connection_string(config: Dict[str, Any]) -> str:
        """
        Build a connection string from a configuration dictionary.
        
        Args:
            config: Database configuration dictionary
            
        Returns:
            Connection string
            
        Raises:
            ValueError: If required configuration is missing
        """
        db_type = config.get("type", "").lower()
        
        if not db_type:
            raise ValueError("Database type is required")
        
        # If URL is already provided, use it
        if config.get("url"):
            return config["url"]
        
        if db_type == "sqlite":
            # SQLite connection string
            db_path = config.get("name", "./intentverse.db")
            if db_path == ":memory:":
                return "sqlite:///:memory:"
            else:
                return f"sqlite:///{db_path}"
        
        elif db_type == "postgresql":
            # PostgreSQL connection string
            host = config.get("host")
            port = config.get("port", "5432")
            database = config.get("name")
            user = config.get("user")
            password = config.get("password")
            
            if not all([host, database]):
                raise ValueError("PostgreSQL requires host and database name")
            
            # Build base URL
            url = "postgresql://"
            if user:
                url += user
                if password:
                    url += f":{password}"
                url += "@"
            url += f"{host}:{port}/{database}"
            
            # Add query parameters
            params = []
            if config.get("ssl_mode"):
                params.append(f"sslmode={config['ssl_mode']}")
            if config.get("application_name"):
                params.append(f"application_name={config['application_name']}")
            if config.get("connect_timeout"):
                params.append(f"connect_timeout={config['connect_timeout']}")
            
            if params:
                url += "?" + "&".join(params)
            
            return url
        
        elif db_type in ["mysql", "mariadb"]:
            # MySQL/MariaDB connection string
            host = config.get("host")
            port = config.get("port", "3306")
            database = config.get("name")
            user = config.get("user")
            password = config.get("password")
            
            if not all([host, database]):
                raise ValueError("MySQL requires host and database name")
            
            # Build base URL
            url = "mysql://"
            if user:
                url += user
                if password:
                    url += f":{password}"
                url += "@"
            url += f"{host}:{port}/{database}"
            
            # Add query parameters
            params = []
            if config.get("charset"):
                params.append(f"charset={config['charset']}")
            if config.get("ssl_mode"):
                params.append(f"ssl_mode={config['ssl_mode']}")
            if config.get("autocommit") is not None:
                params.append(f"autocommit={str(config['autocommit']).lower()}")
            
            if params:
                url += "?" + "&".join(params)
            
            return url
        
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    @staticmethod
    def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize configuration by parsing connection string if provided.
        
        Args:
            config: Raw configuration dictionary
            
        Returns:
            Normalized configuration dictionary
        """
        # If URL is provided, parse it and merge with existing config
        if config.get("url"):
            try:
                parsed_config = DatabaseConfigParser.parse_connection_string(config["url"])
                
                # Merge parsed config with existing config (existing config takes precedence)
                normalized = parsed_config.copy()
                for key, value in config.items():
                    if key != "url" and value is not None:
                        normalized[key] = value
                
                return normalized
            except ValueError as e:
                logging.warning(f"Failed to parse connection string: {e}")
                return config
        
        return config
    
    @staticmethod
    def validate_connection_string_format(connection_string: str) -> tuple[bool, Optional[str]]:
        """
        Validate connection string format without parsing.
        
        Args:
            connection_string: Connection string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not connection_string:
            return False, "Connection string cannot be empty"
        
        try:
            parsed = urlparse(connection_string)
            
            if not parsed.scheme:
                return False, "Connection string must include a scheme"
            
            # Check supported schemes
            supported_schemes = [
                "sqlite", "postgresql", "postgres", "mysql", 
                "mysql+pymysql", "mysql+mysqldb", "mysql+mysqlconnector"
            ]
            
            if parsed.scheme not in supported_schemes:
                return False, f"Unsupported scheme: {parsed.scheme}"
            
            # Validate scheme-specific requirements
            if parsed.scheme == "sqlite":
                # SQLite can have empty or file path
                return True, None
            else:
                # Other databases need hostname
                if not parsed.hostname:
                    return False, f"{parsed.scheme} connection string requires hostname"
                
                # Check for database name (path)
                if not parsed.path or parsed.path == "/":
                    return False, f"{parsed.scheme} connection string requires database name in path"
            
            return True, None
            
        except Exception as e:
            return False, f"Invalid connection string format: {e}"


def parse_database_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and normalize database configuration.
    
    Args:
        config: Raw database configuration
        
    Returns:
        Normalized database configuration
    """
    parser = DatabaseConfigParser()
    return parser.normalize_config(config)