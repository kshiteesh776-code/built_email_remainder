"""
logger_config.py
================
Logging configuration module for the Bulk Email Reminder Tool.

Provides dual output logging:
- Console (StreamHandler) for real-time progress and user feedback.
- File (FileHandler) for persistent audit logs in `email_log.log`.
"""

import logging
import sys
from typing import Optional


def setup_logger(
    log_file: str = "email_log.log",
    log_level: int = logging.INFO,
    logger_name: Optional[str] = "reminder_bot"
) -> logging.Logger:
    """
    Configures and returns a logger instance with console and file handlers.

    :param log_file: Path to the log file (defaults to 'email_log.log').
    :param log_level: Logging level (e.g., logging.INFO, logging.DEBUG).
    :param logger_name: Name of the logger to retrieve or create.
    :return: Configured logging.Logger instance.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    # Cleanly close and remove any existing handlers to prevent unclosed files
    for handler in list(logger.handlers):
        try:
            handler.close()
        except Exception:
            pass
        logger.removeHandler(handler)

    # Formatter pattern: YYYY-MM-DD HH:MM:SS - LEVEL - Message
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler: logs to email_log.log with UTF-8 encoding
    try:
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as e:
        sys.stderr.write(f"Warning: Could not initialize file handler for {log_file}: {e}\n")

    # Console handler: output to standard output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
