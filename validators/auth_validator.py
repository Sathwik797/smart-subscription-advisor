"""Validation helpers for authentication-related requests.

Validation is kept separate from business logic so controllers can reject bad
input early, while services remain focused on domain behavior.
"""

import re

from exceptions.exceptions import ValidationException


class AuthValidator:
    """Validate registration and login inputs before they reach services."""

    @staticmethod
    def validate_registration(data):
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""
        confirm_password = data.get("confirm_password") or ""

        if not username:
            raise ValidationException("Username is required")
        if len(username) < 3:
            raise ValidationException("Username must be at least 3 characters")

        if not email:
            raise ValidationException("Email is required")
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValidationException("Email format is invalid")

        if not password:
            raise ValidationException("Password is required")
        if len(password) < 6:
            raise ValidationException("Password must be at least 6 characters")

        if confirm_password is not None and confirm_password != password:
            raise ValidationException("Passwords do not match")

    @staticmethod
    def validate_login(data):
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""

        if not email:
            raise ValidationException("Email is required")
        if not password:
            raise ValidationException("Password is required")


auth_validator = AuthValidator()
