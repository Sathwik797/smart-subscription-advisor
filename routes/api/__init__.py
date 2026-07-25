"""API blueprint package for JWT-authenticated endpoints."""

from flask import Blueprint

from .auth import api_auth
from .subscriptions import api_subscriptions_bp

api = Blueprint("api", __name__)

api.register_blueprint(api_auth, url_prefix="")
api.register_blueprint(api_subscriptions_bp, url_prefix="")
