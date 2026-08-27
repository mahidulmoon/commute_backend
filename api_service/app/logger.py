import logging
import os
from datetime import datetime

# Ensure log directory exists
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Generate date-wise log file name
log_filename = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")

# Create logger
logger = logging.getLogger("vidlist_ai")
logger.setLevel(logging.INFO)

# Remove any default handlers if already set
if not logger.handlers:
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # File handler (datewise log file)
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# logger.info("Logger initialized successfully.")
