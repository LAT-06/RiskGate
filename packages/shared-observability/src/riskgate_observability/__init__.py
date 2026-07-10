"""Structured logging and correlation-ID helpers (expanded in Milestone 8)."""

import logging


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
