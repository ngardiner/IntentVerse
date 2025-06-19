import os
from typing import Optional

class Config:
    """Configuration management for IntentVerse."""
    
    # Remote Content Pack Repository Configuration
    REMOTE_REPO_URL: str = os.getenv(
        "INTENTVERSE_REMOTE_REPO_URL", 
        "https://raw.githubusercontent.com/ngardiner/IntentVerse-Content/main/"
    )
    
    # Cache configuration
    REMOTE_CACHE_DURATION: int = int(os.getenv("INTENTVERSE_CACHE_DURATION", "300"))  # 5 minutes
    
    # HTTP client configuration
    HTTP_TIMEOUT: float = float(os.getenv("INTENTVERSE_HTTP_TIMEOUT", "30.0"))
    
    # Content pack directory
    CONTENT_PACKS_DIR: Optional[str] = os.getenv("INTENTVERSE_CONTENT_PACKS_DIR")
    
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