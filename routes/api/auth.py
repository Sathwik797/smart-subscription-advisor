"""API routes for registration, login, verification, and password resets using JWT."""

from flask import Blueprint

from controllers.api_controller import (
    api_forgot_password,
    api_login,
    api_register,
    api_resend_verification,
    api_reset_password,
    api_verify_email,
)
from middleware.rate_limiter import limiter

api_auth = Blueprint("api_auth", __name__)


@api_auth.route("/register", methods=["POST"])
def register():
    return api_register()


@api_auth.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    return api_login()


@api_auth.route("/verify-email/<token>", methods=["GET"])
@limiter.limit("20 per minute")
def verify_email(token):
    return api_verify_email(token)


@api_auth.route("/resend-verification", methods=["POST"])
@limiter.limit("3 per hour")
def resend_verification():
    return api_resend_verification()


@api_auth.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per hour")
def forgot_password():
    return api_forgot_password()


@api_auth.route("/reset-password/<token>", methods=["POST"])
@limiter.limit("10 per hour")
def reset_password(token):
    return api_reset_password(token)
