"""API routes for registration and login using JWT."""

from flask import Blueprint

from controllers.api_controller import api_login, api_register

api_auth = Blueprint("api_auth", __name__)


@api_auth.route("/register", methods=["POST"])
def register():
    return api_register()


@api_auth.route("/login", methods=["POST"])
def login():
    return api_login()
