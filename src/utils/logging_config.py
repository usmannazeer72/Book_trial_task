"""
Logging Configuration
"""

import logging
import os
from datetime import datetime

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Create formatters
detailed_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)

simple_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)

# File handler - detailed logs
log_filename = f"logs/book_generation_{datetime.now().strftime('%Y%m%d')}.log"
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(detailed_formatter)

# Console handler - simpler logs
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(simple_formatter)

# Error file handler
error_filename = f"logs/errors_{datetime.now().strftime('%Y%m%d')}.log"
error_handler = logging.FileHandler(error_filename)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(detailed_formatter)


def setup_logger(name):
    """Setup logger with handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.addHandler(error_handler)
    
    return logger
