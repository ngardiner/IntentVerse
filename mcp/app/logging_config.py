import logging
import os
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """
    Configures the root logger to output structured JSON logs to stdout.
    Log level can be set via the LOG_LEVEL environment variable.
    """
    # Get log level from environment variable, default to INFO
    log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    
    log = logging.getLogger()
    log.setLevel(log_level)

    # Use a handler that outputs to stdout
    handler = logging.StreamHandler(sys.stdout)

    # Define the fields to include in the JSON output.
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s"
    )

    handler.setFormatter(formatter)

    # Avoid adding duplicate handlers
    if not log.handlers:
        log.addHandler(handler)