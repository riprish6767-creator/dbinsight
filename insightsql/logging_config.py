from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time


def configure_logging(log_path: Path) -> None:
    logger = logging.getLogger("insightsql")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if any(getattr(handler, "baseFilename", None) == str(log_path) for handler in logger.handlers):
        return

    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_path, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    )
    handler.formatter.converter = time.gmtime
    logger.addHandler(handler)
