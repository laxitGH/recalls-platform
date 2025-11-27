import json
import logging
import os
import sys
from typing import Any, Dict

_INITIALIZED = False


def _init_root_logger() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers to avoid duplicate logs when reloaded
    root.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stdout)
    fmt = os.getenv("LOG_FORMAT", "text").lower()
    if fmt == "json":
        formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    _INITIALIZED = True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # If extra props were provided via record.__dict__["props"]
        props = getattr(record, "props", None)
        if isinstance(props, dict) and props:
            payload.update(props)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    _init_root_logger()
    return logging.getLogger(name)


def kv_message(message: str, **fields: Any) -> str:
    """Return message with appended JSON key-values for quick, readable context."""
    if not fields:
        return message
    return f"{message} | {json.dumps(fields, ensure_ascii=False, sort_keys=True)}"


