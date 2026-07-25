"""Centralized logging configuration for the Flask application.

This module provides a single logger instance that can be reused across the
application layers. It writes to both the console and a rotating file so that
local development and later monitoring both benefit from the same output.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import request


LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "application.log")


def _build_logger():
    """Create and configure the shared application logger."""
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("subscription_assistant")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(module)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = _build_logger()


def log_request_data(app):
    """Register request lifecycle hooks that log API traffic."""

    @app.before_request
    def log_before_request():
        if not request.path.startswith("/api"):
            return

        request.start_time = None
        request.start_time = __import__("time").perf_counter()

        user_id = None
        if hasattr(request, "headers"):
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                user_id = "<jwt-present>"
            elif hasattr(request, "user") and request.user is not None:
                user_id = getattr(request.user, "id", None)

        logger.info(
            "API request %s %s started endpoint=%s user=%s",
            request.method,
            request.path,
            request.endpoint or "unknown",
            user_id or "anonymous",
        )

    @app.after_request
    def log_after_request(response):
        if not request.path.startswith("/api"):
            return response

        duration_ms = 0
        if getattr(request, "start_time", None) is not None:
            duration_ms = round((__import__("time").perf_counter() - request.start_time) * 1000, 2)

        user_id = None
        if hasattr(request, "headers"):
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                user_id = "<jwt-present>"
            elif hasattr(request, "user") and request.user is not None:
                user_id = getattr(request.user, "id", None)

        logger.info(
            "API request %s %s completed status=%s duration_ms=%.2f endpoint=%s user=%s",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            request.endpoint or "unknown",
            user_id or "anonymous",
        )
        return response
