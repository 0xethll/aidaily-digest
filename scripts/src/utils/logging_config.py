"""
Shared logging configuration for AI Daily Digest scripts
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    include_console: bool = True
) -> logging.Logger:
    """
    Configure logging with consistent format across all scripts
    
    Args:
        level: Logging level (default: INFO)
        log_file: Optional log file path
        include_console: Whether to include console output (default: True)
    
    Returns:
        Configured logger instance
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    handlers = []
    
    # Add console handler if requested
    if include_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    # Add file handler if log file specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Add handlers to logger
    for handler in handlers:
        logger.addHandler(handler)
    
    return logger


def get_script_logger(script_name: str) -> logging.Logger:
    """
    Get a logger for a specific script
    
    Args:
        script_name: Name of the script/module
        
    Returns:
        Logger instance for the script
    """
    return logging.getLogger(script_name)