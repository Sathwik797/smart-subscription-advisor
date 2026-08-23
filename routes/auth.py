"""Routing layer for authentication and account-related URLs.

Routes stay thin and delegate request handling to controller functions so the
business logic remains in the service layer.
"""

from flask import Blueprint
from middleware.auth import current_user, login_required

from controllers.auth_controller import (
    dashboard as dashboard_controller,
    edit_profile as edit_profile_controller,
    forgot_password as forgot_password_controller,
    login as login_controller,
    logout as logout_controller,
    profile as profile_controller,
    register as register_controller,
    resend_verification as resend_verification_controller,
    reset_password as reset_password_controller,
    verify_email as verify_email_controller,
)
from middleware.rate_limiter import limiter

auth = Blueprint("auth", __name__)


@auth.app_context_processor
def inject_current_user():
    return dict(current_user=current_user)



@auth.route("/register", methods=["GET", "POST"])
def register():
    return register_controller()


@auth.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    return login_controller()


@auth.route("/verify-email/<token>", methods=["GET"])
@limiter.limit("20 per minute")
def verify_email(token):
    return verify_email_controller(token)


@auth.route("/resend-verification", methods=["GET", "POST"])
@limiter.limit("3 per hour")
def resend_verification():
    return resend_verification_controller()


@auth.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def forgot_password():
    return forgot_password_controller()


@auth.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def reset_password(token):
    return reset_password_controller(token)


@auth.route("/dashboard")
@login_required
def dashboard():
    return dashboard_controller()


@auth.route("/profile")
@login_required
def profile():
    return profile_controller()


@auth.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    return edit_profile_controller()


@auth.route("/logout")
@login_required
def logout():
    return logout_controller()
