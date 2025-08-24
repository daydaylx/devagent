from __future__ import annotations
import logging
from rich.logging import RichHandler

_DEF_FORMAT = "%(message)s"

_logger: logging.Logger | None = None

def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        logging.basicConfig(
            level=logging.INFO,
            format=_DEF_FORMAT,
            datefmt="%H:%M:%S",
            handlers=[RichHandler(rich_tracebacks=True, markup=True)],
        )
        _logger = logging.getLogger("devagent")
    return _logger
