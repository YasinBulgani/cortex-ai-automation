"""Centralized logging utility."""

import logging

_loggers = {}


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger instance."""
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]
