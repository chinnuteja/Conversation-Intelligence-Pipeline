"""Central logging configuration for the pipeline."""

import logging
import os
import sys


class _FlushingStreamHandler(logging.StreamHandler):
    """Flush after every record so IDE / captured terminals show progress immediately."""

    def emit(self, record):
        super().emit(record)
        try:
            self.flush()
        except OSError:
            pass


def setup_logging(level: str | None = None) -> None:
    """Configure root logger once (idempotent for repeated calls)."""
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(log_level)
        return
    handler = _FlushingStreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(log_level)
