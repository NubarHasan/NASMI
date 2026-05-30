from __future__ import annotations

import json
import logging
import traceback
from collections.abc import MutableMapping
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from typing import Any

from core.paths import APP_LOG_FILE, AUDIT_LOG_FILE, ERROR_LOG_FILE, LOGS_DIR
from core.types import ComponentName, EntityId, FilePath, JobId

_MAX_BYTES: int = 10 * 1024 * 1024
_BACKUP_COUNT: int = 5

_LOGGER_APP: str = "nasmi.app"
_LOGGER_AUDIT: str = "nasmi.audit"
_LOGGER_ERROR: str = "nasmi.error"

_STANDARD_ATTRS: frozenset[str] = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "taskName",
    }
)


class JsonFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        extra = {k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS}

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "extra": extra,
        }

        if record.exc_info:
            payload["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(payload, ensure_ascii=False, default=str)


class NasmiLoggerAdapter(logging.LoggerAdapter[logging.Logger]):

    def __init__(
        self,
        logger: logging.Logger,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(logger, context or {})

    def process(
        self,
        msg: Any,
        kwargs: MutableMapping[str, Any],
    ) -> tuple[Any, MutableMapping[str, Any]]:
        base: dict[str, Any] = dict(self.extra or {})
        extra = kwargs.get("extra")
        if not isinstance(extra, dict):
            extra = {}
        kwargs["extra"] = {**base, **extra}
        return msg, kwargs

    def bind(self, **context: Any) -> NasmiLoggerAdapter:
        base: dict[str, Any] = dict(self.extra or {})
        merged: dict[str, Any] = {**base, **context}
        return NasmiLoggerAdapter(self.logger, merged)


def _make_rotating_handler(filepath: FilePath) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        filepath,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(JsonFormatter())
    return handler


def _build_logger(
    name: str,
    filepath: FilePath,
    level: int,
) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        logger.handlers.clear()
    logger.setLevel(level)
    logger.addHandler(_make_rotating_handler(filepath))
    logger.propagate = False
    return logger


def get_app_logger() -> NasmiLoggerAdapter:
    return NasmiLoggerAdapter(logging.getLogger(_LOGGER_APP))


def get_audit_logger() -> NasmiLoggerAdapter:
    return NasmiLoggerAdapter(logging.getLogger(_LOGGER_AUDIT))


def get_error_logger() -> NasmiLoggerAdapter:
    return NasmiLoggerAdapter(logging.getLogger(_LOGGER_ERROR))


def log_audit_event(
    message: str,
    entity_id: EntityId | None = None,
    job_id: JobId | None = None,
    component: ComponentName | None = None,
    **kwargs: Any,
) -> None:
    get_audit_logger().bind(
        entity_id=entity_id,
        job_id=job_id,
        component=component,
        **kwargs,
    ).info(message)


def log_exception(
    exc: Exception,
    message: str = "unhandled_exception",
    entity_id: EntityId | None = None,
    job_id: JobId | None = None,
    component: ComponentName | None = None,
    **kwargs: Any,
) -> None:
    get_error_logger().bind(
        entity_id=entity_id,
        job_id=job_id,
        component=component,
        **kwargs,
    ).error(message, exc_info=(type(exc), exc, exc.__traceback__))


def configure_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    _build_logger(_LOGGER_APP, APP_LOG_FILE, logging.INFO)
    _build_logger(_LOGGER_AUDIT, AUDIT_LOG_FILE, logging.INFO)
    _build_logger(_LOGGER_ERROR, ERROR_LOG_FILE, logging.ERROR)
