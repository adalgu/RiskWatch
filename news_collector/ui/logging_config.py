"""
Logging configuration module for the dashboard application.
Provides centralized logging setup with both file and console handlers.
"""

import logging
import logging.handlers
import os
import sys
from typing import Optional


def setup_logging(
    log_dir: str = 'logs',
    log_file: str = 'dashboard.log',
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    file_level: int = logging.DEBUG,
    console_level: int = logging.INFO
) -> logging.Logger:
    """
    Configure and set up logging with both file and console handlers.

    Args:
        log_dir: Directory to store log files
        log_file: Name of the log file
        max_bytes: Maximum size of each log file
        backup_count: Number of backup files to keep
        file_level: Logging level for file handler
        console_level: Logging level for console handler

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )

    # Create handlers
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, log_file),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(file_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(console_level)

    # Configure root logger
    root_logger = logging.getLogger('dashboard')
    root_logger.setLevel(logging.DEBUG)

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers = []

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger


# Create and configure the logger instance
logger = setup_logging()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    If no name is provided, returns the root dashboard logger.

    Args:
        name: Name for the logger (optional)

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f'dashboard.{name}')
    return logger
