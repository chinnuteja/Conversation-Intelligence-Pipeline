"""Central logging configuration for the pipeline."""

import logging
import os


def setup_logging(level: str | None = None) -> None:
    """Configure root logger once (idempotent for repeated calls)."""
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(log_level)
        return
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
