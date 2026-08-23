"""API route for the Subscription Advisor chatbot.

Registered under the /api blueprint so it inherits the /api prefix
and is protected by JWT authentication via the controller decorator.
"""

from flask import Blueprint

from controllers.chat_controller import chat

api_chat_bp = Blueprint("api_chat", __name__)


@api_chat_bp.route("/chat", methods=["POST"])
def chat_endpoint():
    """POST /api/chat — Subscription Advisor chatbot."""
    return chat()
