"""Centralized structlog configuration."""

import logging
import sys

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Set up structlog for the whole app. Call once, near the entry point."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a logger. Use the module name (__name__) as the conventional name."""
    return structlog.get_logger(name)
