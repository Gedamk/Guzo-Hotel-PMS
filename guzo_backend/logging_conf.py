# guzo_backend/logging_conf.py

import logging
import logging.config
import os
from pathlib import Path

LOG_DIR = Path(os.getenv("GUZO_LOG_DIR", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING_CONFIG = {
  "version": 1,
  "disable_existing_loggers": False,
  "formatters": {
    "standard": {
      "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    },
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "formatter": "standard",
      "level": "INFO",
    },
    "backend_file": {
      "class": "logging.handlers.RotatingFileHandler",
      "formatter": "standard",
      "level": "INFO",
      "filename": str(LOG_DIR / "backend.log"),
      "maxBytes": 5_000_000,
      "backupCount": 5,
      "encoding": "utf-8",
    },
    "reports_file": {
      "class": "logging.handlers.RotatingFileHandler",
      "formatter": "standard",
      "level": "INFO",
      "filename": str(LOG_DIR / "reports.log"),
      "maxBytes": 5_000_000,
      "backupCount": 5,
      "encoding": "utf-8",
    },
  },
  "loggers": {
    "uvicorn": {
      "handlers": ["console"],
      "level": "INFO",
      "propagate": False,
    },
    "guzo.backend": {
      "handlers": ["console", "backend_file"],
      "level": "INFO",
      "propagate": False,
    },
    "guzo.reports": {
      "handlers": ["console", "reports_file"],
      "level": "INFO",
      "propagate": False,
    },
  },
  "root": {
    "handlers": ["console"],
    "level": "WARNING",
  },
}


def setup_logging():
  logging.config.dictConfig(LOGGING_CONFIG)
