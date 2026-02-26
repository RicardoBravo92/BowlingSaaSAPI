import logging
import sys
from typing import Any

# Custom log format that looks professional
LOG_FORMAT = "%(levelname)s:     %(asctime)s - %(name)s - %(message)s"

def setup_logging():
    """Sets up the logging configuration for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # You can also configure specific loggers here
    # Example: sqlalchemy.engine level to WARNING to avoid too much noise in production
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """Returns a logger instance with the given name."""
    return logging.getLogger(name)
