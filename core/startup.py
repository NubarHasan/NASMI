from core.logging import get_logger, initialize_logging
from core.paths import paths
from core.settings import settings

logger = get_logger("startup")


def _create_directories() -> None:
    for directory in paths.directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug("Directory ready: %s", directory)


def _verify_structure() -> None:
    missing = [d for d in paths.directories if not d.exists()]
    if missing:
        for directory in missing:
            logger.error("Missing directory: %s", directory)
        raise RuntimeError("Project structure verification failed")
    logger.debug("Project structure verified")


def _startup_banner() -> None:
    logger.info("=" * 52)
    logger.info("  %s  v%s", settings.app.name, settings.app.version)
    logger.info("  %s", settings.app.description)
    logger.info("  Root: %s", paths.root)
    logger.info("=" * 52)


def run() -> None:
    initialize_logging()
    _create_directories()
    _verify_structure()
    _startup_banner()
