import logging
import json
import time
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno
        }
        
        # Include exception details if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # Include extra attributes passed to log call
        if hasattr(record, "extra_info"):
            log_data["extra_info"] = record.extra_info
            
        return json.dumps(log_data)

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Check if there is already a handler (e.g. from uvicorn or parent) to prevent duplicates
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    else:
        # Update existing handlers to use JSONFormatter
        for handler in logger.handlers:
            handler.setFormatter(JSONFormatter())
            
    # Configure third-party loggers to use structured format as well
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        l = logging.getLogger(logger_name)
        for h in l.handlers:
            h.setFormatter(JSONFormatter())
