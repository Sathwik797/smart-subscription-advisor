"""Global error handlers for the Flask application.

These handlers translate custom exceptions into consistent JSON responses for
API requests while leaving HTML pages to behave as before.
"""

from flask import jsonify, request
from werkzeug.exceptions import HTTPException

from logging_config.logger import logger as app_logger
from flask_jwt_extended.exceptions import CSRFError
from .exceptions import (
    AppException,
    AuthenticationException,
    AuthorizationException,
    DatabaseException,
    ResourceNotFoundException,
    ValidationException,
)

def register_error_handlers(app):
    """Register centralized exception handlers on the Flask app."""

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        app_logger.warning("CSRF validation failed on %s %s: %s", request.method, request.path, str(error))
        return jsonify({"success": False, "message": "CSRF token missing or invalid"}), 400

    @app.errorhandler(ValidationException)
    def handle_validation_error(error):
        app_logger.warning("Validation failed: %s", error.message)
        if request.path.startswith("/api"):
            return jsonify({"success": False, "message": error.message}), error.status_code
        return jsonify({"success": False, "message": error.message}), error.status_code

    @app.errorhandler(AuthenticationException)
    def handle_authentication_error(error):
        if request.path.startswith("/api"):
            return jsonify({"success": False, "message": error.message}), error.status_code
        return jsonify({"success": False, "message": error.message}), error.status_code

    @app.errorhandler(AuthorizationException)
    def handle_authorization_error(error):
        if request.path.startswith("/api"):
            return jsonify({"success": False, "message": error.message}), error.status_code
        return jsonify({"success": False, "message": error.message}), error.status_code

    @app.errorhandler(ResourceNotFoundException)
    def handle_not_found_error(error):
        if request.path.startswith("/api"):
            return jsonify({"success": False, "message": error.message}), error.status_code
        return jsonify({"success": False, "message": error.message}), error.status_code

    @app.errorhandler(DatabaseException)
    def handle_database_error(error):
        app_logger.exception("Database exception occurred")
        if request.path.startswith("/api"):
            return jsonify({"success": False, "message": error.message}), error.status_code
        return jsonify({"success": False, "message": error.message}), error.status_code

    @app.errorhandler(AppException)
    def handle_app_exception(error):
        if request.path.startswith("/api"):
            return jsonify({"success": False, "message": error.message}), error.status_code
        return jsonify({"success": False, "message": error.message}), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        if request.path.startswith("/api"):
            return jsonify({"success": False, "message": error.description}), error.code
        return jsonify({"success": False, "message": error.description}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app_logger.exception("Unhandled exception occurred")
        if request.path.startswith("/api"):
            return jsonify({"success": False, "message": "Internal server error"}), 500
        return jsonify({"success": False, "message": "Internal server error"}), 500
