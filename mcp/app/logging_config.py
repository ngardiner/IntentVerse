import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """
    Configures the root logger to output structured JSON logs to stdout.
    """
    log = logging.getLogger()
    log.setLevel(logging.INFO)

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