import logging
import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def configure_test_logging():
    """
    Configure logging for tests based on environment variables.
    This is automatically applied to all tests.
    """
    # Get log level from environment variable, default to INFO
    log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    # Configure root logger
    logging.getLogger().setLevel(log_level)
    
    # Configure specific loggers that might be too verbose
    if log_level == logging.ERROR:
        # These loggers are particularly noisy, so we set them to ERROR level
        for logger_name in ["httpx", "urllib3", "sqlalchemy.engine"]:
            logging.getLogger(logger_name).setLevel(logging.ERROR)