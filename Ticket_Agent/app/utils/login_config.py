import logging
import colorlog
import os
from logging.handlers import TimedRotatingFileHandler


def setup_logging():
    """Setup logging configuration with daily rotating log file in Ticket_Agent/Logs/app.log.YYYY-MM-DD"""

        # Root project directory (Ticket_Agent)
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

    # Logs directory in root
    logs_dir = os.path.join(root_dir, "Logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Base log file (with TimedRotatingFileHandler it will save as app.log.YYYY-MM-DD)
    log_file = os.path.join(logs_dir, "app.log")


    # Define log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    colored_format = "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s"

    # Create formatters
    formatter = logging.Formatter(log_format)
    colored_formatter = colorlog.ColoredFormatter(
        colored_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "white",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )

    # File handler → rotates daily, keeps 30 backups
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        utc=False,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"  # → app.log.2025-09-08

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(colored_formatter)

    # Root logger setup
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers
    if not root_logger.handlers:
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    # Adjust noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)

    return root_logger


def get_logger(name):
    """Get a logger with the specified name"""
    return logging.getLogger(name)
