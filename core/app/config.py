import os
from typing import Optional


class Config:
    """Configuration management for IntentVerse."""

    # Remote Content Pack Repository Configuration
    REMOTE_REPO_URL: str = os.getenv(
        "INTENTVERSE_REMOTE_REPO_URL",
        "https://raw.githubusercontent.com/ngardiner/IntentVerse-Content/main/",
    )

    # Cache configuration
    REMOTE_CACHE_DURATION: int = int(
        os.getenv("INTENTVERSE_CACHE_DURATION", "300")
    )  # 5 minutes

    # HTTP client configuration
    HTTP_TIMEOUT: float = float(os.getenv("INTENTVERSE_HTTP_TIMEOUT", "30.0"))

    # Content pack directory
    CONTENT_PACKS_DIR: Optional[str] = os.getenv("INTENTVERSE_CONTENT_PACKS_DIR")

    # Database configuration
    DB_TYPE: str = os.getenv("INTENTVERSE_DB_TYPE", "sqlite")
    DB_URL: Optional[str] = os.getenv("INTENTVERSE_DB_URL")
    DB_HOST: Optional[str] = os.getenv("INTENTVERSE_DB_HOST")
    DB_PORT: Optional[str] = os.getenv("INTENTVERSE_DB_PORT")
    DB_NAME: Optional[str] = os.getenv("INTENTVERSE_DB_NAME")
    DB_USER: Optional[str] = os.getenv("INTENTVERSE_DB_USER")
    DB_PASSWORD: Optional[str] = os.getenv("INTENTVERSE_DB_PASSWORD")
    DB_SSL_MODE: Optional[str] = os.getenv("INTENTVERSE_DB_SSL_MODE")
    
    # PostgreSQL-specific configuration (v1.2.0)
    DB_POOL_SIZE: int = int(os.getenv("INTENTVERSE_DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("INTENTVERSE_DB_MAX_OVERFLOW", "20"))
    DB_POOL_RECYCLE: int = int(os.getenv("INTENTVERSE_DB_POOL_RECYCLE", "3600"))
    DB_CONNECT_TIMEOUT: Optional[int] = int(os.getenv("INTENTVERSE_DB_CONNECT_TIMEOUT", "30")) if os.getenv("INTENTVERSE_DB_CONNECT_TIMEOUT") else None
    DB_APPLICATION_NAME: str = os.getenv("INTENTVERSE_DB_APPLICATION_NAME", "IntentVerse")

    @classmethod
    def get_remote_repo_url(cls) -> str:
        """Get the remote repository URL."""
        return cls.REMOTE_REPO_URL

    @classmethod
    def get_manifest_url(cls) -> str:
        """Get the remote manifest URL."""
        from urllib.parse import urljoin

        return urljoin(cls.REMOTE_REPO_URL, "manifest.json")

    @classmethod
    def get_cache_duration(cls) -> int:
        """Get the cache duration in seconds."""
        return cls.REMOTE_CACHE_DURATION

    @classmethod
    def get_http_timeout(cls) -> float:
        """Get the HTTP timeout in seconds."""
        return cls.HTTP_TIMEOUT

    @classmethod
    def get_database_type(cls) -> str:
        """Get the database type (sqlite, postgresql, mysql)."""
        return cls.DB_TYPE.lower()

    @classmethod
    def get_database_url(cls) -> Optional[str]:
        """Get the complete database URL if provided."""
        return cls.DB_URL

    @classmethod
    def get_database_config(cls) -> dict:
        """Get database configuration as a dictionary with enhanced parsing."""
        # Build raw configuration
        raw_config = {
            "type": cls.get_database_type(),
            "url": cls.DB_URL,
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "name": cls.DB_NAME,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
            "ssl_mode": cls.DB_SSL_MODE,
        }
        
        # Add database-specific configuration
        db_type = cls.get_database_type()
        
        if db_type == "postgresql":
            raw_config.update({
                "pool_size": cls.DB_POOL_SIZE,
                "max_overflow": cls.DB_MAX_OVERFLOW,
                "pool_recycle": cls.DB_POOL_RECYCLE,
                "connect_timeout": cls.DB_CONNECT_TIMEOUT,
                "application_name": cls.DB_APPLICATION_NAME,
            })
        
        elif db_type in ["mysql", "mariadb"]:
            raw_config.update({
                "pool_size": cls.DB_POOL_SIZE,
                "max_overflow": cls.DB_MAX_OVERFLOW,
                "pool_recycle": cls.DB_POOL_RECYCLE,
                "connect_timeout": cls.DB_CONNECT_TIMEOUT,
                "charset": os.getenv("INTENTVERSE_DB_CHARSET", "utf8mb4"),
                "sql_mode": os.getenv("INTENTVERSE_DB_SQL_MODE", "STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO"),
                "autocommit": os.getenv("INTENTVERSE_DB_AUTOCOMMIT", "false").lower() == "true",
            })
        
        # Parse and normalize configuration (handles connection strings)
        from .config_parser import parse_database_config
        return parse_database_config(raw_config)
    
    @classmethod
    def validate_database_config(cls) -> tuple[bool, list[str], list[str]]:
        """
        Validate the current database configuration.
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        from .database.validation import validate_database_config
        
        config = cls.get_database_config()
        return validate_database_config(config)

    @classmethod
    def get_default_sqlite_url(cls) -> str:
        """Get the default SQLite database URL."""
        return "sqlite:///./intentverse.db"
