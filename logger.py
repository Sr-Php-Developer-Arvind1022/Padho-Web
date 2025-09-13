import logging
import os

# Step 1: Define log path
LOG_DIR = "logs"
LOG_FILE = "api.log"
os.makedirs(LOG_DIR, exist_ok=True)
log_path = os.path.join(LOG_DIR, LOG_FILE)

# Step 2: Create named logger
logger = logging.getLogger("logger")
logger.setLevel(logging.INFO)  # ✅ Explicitly set level

# Step 3: Add handlers only once (avoid duplicate logs if imported multiple times)
if not logger.handlers:
    file_handler = logging.FileHandler(log_path)
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# ✅ Step 4: Prevent double logging if using root logger somewhere else
logger.propagate = False