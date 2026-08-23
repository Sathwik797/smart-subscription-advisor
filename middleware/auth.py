"""JWT authentication middleware for web and API requests.

Provides the `@login_required` decorator that authenticates users via JWT (cookies or headers),
binds the authenticated user to Flask's `g.current_user`, and exposes a `current_user` proxy.
"""

from functools import wraps
from flask import flash, g, jsonify, redirect, request, url_for
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from werkzeug.local import LocalProxy

from logging_config.logger import logger
from services.auth_service import auth_service


class AnonymousUser:
    """Represents an unauthenticated user session."""
    is_authenticated = False
    is_anonymous = True
    is_active = False
    id = None
    username = ""
    email = ""
    mobile_number = ""
    occupation = ""
    financial_preference = ""


def _get_current_user():
    """Retrieve the current user from Flask's request context."""
    user = getattr(g, "current_user", None)
    if user is not None:
        return user
    return AnonymousUser()


current_user = LocalProxy(_get_current_user)


def resolve_current_user():
    """Attempt to resolve and set g.current_user from JWT in cookies or headers."""
    # If neither Authorization header nor non-empty access_token_cookie is present, user is anonymous
    auth_header = request.headers.get("Authorization", "")
    cookie_token = request.cookies.get("access_token_cookie", "")
    if not auth_header and not cookie_token:
        g.current_user = AnonymousUser()
        return g.current_user

    try:
        verify_jwt_in_request(optional=True, locations=["cookies", "headers"])
        identity = get_jwt_identity()
        if identity is not None:
            user = auth_service.get_user_by_id(int(identity))
            if user:
                g.current_user = user
                return user
    except Exception as exc:
        logger.debug("Failed to resolve JWT current user: %s", exc)

    g.current_user = AnonymousUser()
    return g.current_user


def login_required(fn):
    """Decorator to enforce JWT authentication on web and API endpoints."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = resolve_current_user()
        if user and user.is_authenticated:
            return fn(*args, **kwargs)

        # Distinguish between API/AJAX requests and browser page requests
        if request.path.startswith("/api") or request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": "Missing or invalid authentication token"}), 401

        flash("Please log in to access this page.", "warning")
        return redirect(url_for("auth.login"))

    return wrapper
