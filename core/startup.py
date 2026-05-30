from __future__ import annotations

from core.logging import configure_logging, get_app_logger
from core.paths import (
    ARCHIVE_DIR,
    CONFIG_DIR,
    DATA_DIR,
    EXPORTS_DIR,
    EXTRACTION_DIR,
    FORMS_DIR,
    KNOWLEDGE_DIR,
    LOGS_DIR,
    MODELS_DIR,
    OCR_DIR,
    PACKAGES_DIR,
    RECORDS_DIR,
    REVIEW_DIR,
    TEMP_DIR,
    TEMPLATES_DIR,
    VAULT_DIR,
)

_REQUIRED_DIRS = (
    DATA_DIR,
    LOGS_DIR,
    TEMP_DIR,
    CONFIG_DIR,
    ARCHIVE_DIR,
    OCR_DIR,
    EXTRACTION_DIR,
    REVIEW_DIR,
    KNOWLEDGE_DIR,
    RECORDS_DIR,
    PACKAGES_DIR,
    EXPORTS_DIR,
    FORMS_DIR,
    TEMPLATES_DIR,
    MODELS_DIR,
    VAULT_DIR,
)


def _create_directories() -> None:
    for directory in _REQUIRED_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


def bootstrap() -> None:
    configure_logging()
    _create_directories()
    logger = get_app_logger().bind(component="startup")
    logger.info("NASMI bootstrap complete")
