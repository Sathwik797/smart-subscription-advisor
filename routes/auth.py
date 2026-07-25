"""Routing layer for authentication and account-related URLs.

Routes stay thin and delegate request handling to controller functions so the
business logic remains in the service layer.
"""

from flask import Blueprint
from flask_login import login_required

from controllers.auth_controller import (
    dashboard as dashboard_controller,
    edit_profile as edit_profile_controller,
    login as login_controller,
    logout as logout_controller,
    profile as profile_controller,
    register as register_controller,
)


auth = Blueprint("auth", __name__)


@auth.route("/register", methods=["GET", "POST"])
def register():
    return register_controller()


@auth.route("/login", methods=["GET", "POST"])
def login():
    return login_controller()


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
