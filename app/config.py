from dotenv import load_dotenv
import os


load_dotenv()

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:////data/app.db")

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

if not WEBHOOK_SECRET:
    raise ValueError(
        "WEBHOOK_SECRET environment variable is not set. "
        "The app cannot start without it. "
        "Set it in your .env file or docker-compose.yml."
    )
 
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is not set. "
        "Example value: sqlite:////data/app.db"
    )

ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
 
if LOG_LEVEL not in ALLOWED_LOG_LEVELS:
    raise ValueError(
        f"LOG_LEVEL must be one of {ALLOWED_LOG_LEVELS}. "
        f"Got: '{LOG_LEVEL}'"
    )