import logging
import json
from datetime import datetime
from app.config import LOG_LEVEL

class JSONFormatter(logging.Formatter):
    def format(self,record):
        log_data = {
            "ts" :datetime.utcnow().isoformat() + "Z",
            "level" : record.levelname,
            "message":record.getMessage(),
        }
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        return json.dumps(log_data)


handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())

logger = logging.getLogger("app")
logger.setLevel(LOG_LEVEL)
logger.addHandler(handler)
