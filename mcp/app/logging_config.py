import logging
import os
import sys
from pythonjsonlogger import jsonlogger


def setup_logging(stdio_mode=False):
    """
    Configures the root logger to output structured JSON logs.
    Log level can be set via the LOG_LEVEL environment variable.
    
    Args:
        stdio_mode: If True, logs to file to avoid interfering with MCP stdio protocol.
                   If False, logs to stdout for normal operation.
    """
    # Get log level from environment variable, default to INFO
    import os
    log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    log = logging.getLogger()
    log.setLevel(log_level)

    if stdio_mode:
        # In stdio mode, log to file to avoid any interference with MCP protocol
        from pathlib import Path
        # Use absolute path to ensure logs go to project root logs directory
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        handler = logging.FileHandler(log_dir / "mcp-stdio.log", mode='a')
    else:
        # Normal mode, log to stdout
        handler = logging.StreamHandler(sys.stdout)

    # Define the fields to include in the JSON output.
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s"
    )

    handler.setFormatter(formatter)

    # Avoid adding duplicate handlers
    if not log.handlers:
        log.addHandler(handler)
