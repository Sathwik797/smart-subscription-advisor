"""Controller for the /api/chat endpoint.

Follows the same pattern as api_controller.py:
  - Validates request input.
  - Resolves authenticated user via JWT.
  - Delegates to the chat service.
  - Returns a consistent JSON response.
  - Never exposes provider errors, system prompts, or stack traces.
"""

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from exceptions.exceptions import ValidationException
from logging_config.logger import logger
from services.auth_service import auth_service
from services.chat_service import get_chat_response


def json_success(data, status_code=200):
    """Return a standard success envelope."""
    return jsonify({"success": True, "data": data}), status_code


def json_error(message, status_code=400):
    """Return a standard error envelope."""
    return jsonify({"success": False, "message": message}), status_code


@jwt_required()
def chat():
    """Handle POST /api/chat — the Subscription Advisor chatbot endpoint."""
    payload = request.get_json(silent=True) or {}

    message = (payload.get("message") or "").strip()
    page = (payload.get("page") or "").strip() or None

    # Input validation
    if not message:
        raise ValidationException("Message is required and cannot be empty.")

    if len(message) > 2000:
        raise ValidationException("Message is too long. Please keep it under 2000 characters.")

    # Resolve authenticated user — never trust user_id from the frontend
    user_id = get_jwt_identity()
    user = auth_service.get_user_by_id(user_id)

    logger.info("Chat request received — page_context=%s", page or "none")

    response_text = get_chat_response(user=user, message=message, page=page)

    return json_success({"response": response_text})
